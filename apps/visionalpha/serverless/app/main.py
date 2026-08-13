from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .database import (
    create_asset,
    get_history,
    get_job,
    is_configured,
    queue_asset,
    save_analysis,
)
from .pipeline import analyze_video
from .storage import create_signed_upload

app = FastAPI(title="VisionAlpha API", version="0.3.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://visionalpha.vercel.app",
        "https://visionalpha-oluwatosin-s-projects-31b5c057.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

SUPPORTED_VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
UPLOAD_BUCKET = "visionalpha-video"
TUS_CHUNK_BYTES = 6 * 1024 * 1024


class UploadSignRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = None
    size_bytes: int = Field(ge=1)
    location_id: str | None = None


class JobRequest(BaseModel):
    asset_id: str = Field(min_length=1)


def _overview_from_history(rows: list[dict]) -> dict | None:
    values = [float(row["activity_index"]) for row in rows if row.get("activity_index") is not None]
    if not values:
        return None

    latest = values[-1]
    first = values[0]
    change = ((latest - first) / max(abs(first), 1e-6)) * 100 if len(values) > 1 else 0.0
    if latest >= 55:
        regime = "economic_expansion"
    elif latest <= 45:
        regime = "economic_contraction"
    else:
        regime = "neutral"

    return {
        "economic_activity_index": round(latest, 2),
        "change_30d": round(change, 2),
        "regime": regime,
        "signal": {
            "name": "Observed Physical Activity",
            "direction": "bullish" if latest >= 55 else "bearish" if latest <= 45 else "neutral",
            "confidence": round(min(0.95, 0.5 + abs(latest - 50) / 100), 2),
        },
        "mode": "persisted_observations",
        "observations": len(values),
    }


def _semantic_enabled() -> bool:
    return os.getenv("ENABLE_SEMANTIC_UPLOADS", "0").strip().lower() in {"1", "true", "yes", "on"}


def _require_semantic() -> None:
    if not _semantic_enabled():
        raise HTTPException(
            status_code=503,
            detail="Full Engine uploads are disabled until the semantic worker is deployed",
        )
    if not is_configured():
        raise HTTPException(status_code=503, detail="Supabase persistence is not configured")


@app.get("/health")
def health() -> dict:
    if _semantic_enabled() and is_configured():
        semantic_queue = "enabled"
    elif _semantic_enabled():
        semantic_queue = "unconfigured"
    else:
        semantic_queue = "disabled"

    return {
        "status": "ok",
        "service": "visionalpha-api",
        "mode": "serverless_motion_proxy",
        "persistence": "supabase" if is_configured() else "unconfigured",
        "semantic_queue": semantic_queue,
    }


@app.get("/api/v1/history")
def history(limit: int = 30) -> dict:
    try:
        rows = get_history(limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "items": rows,
        "count": len(rows),
        "persistence": "supabase" if is_configured() else "unconfigured",
    }


@app.get("/api/v1/overview")
def overview() -> dict:
    try:
        persisted = _overview_from_history(get_history(30))
    except RuntimeError:
        persisted = None
    if persisted:
        return persisted
    return {
        "economic_activity_index": 82.41,
        "change_30d": 3.82,
        "regime": "economic_expansion",
        "signal": {
            "name": "Nigeria Industrial Activity",
            "direction": "bullish",
            "confidence": 0.87,
        },
        "mode": "seeded_demo",
    }


@app.post("/api/v1/uploads/sign")
def sign_semantic_upload(payload: UploadSignRequest) -> dict:
    _require_semantic()
    suffix = Path(payload.filename).suffix.lower()
    if suffix not in SUPPORTED_VIDEO_SUFFIXES:
        raise HTTPException(status_code=415, detail="Unsupported video format")

    max_bytes = int(os.getenv("MAX_SEMANTIC_UPLOAD_BYTES", str(1024 * 1024 * 1024)))
    if payload.size_bytes > max_bytes:
        raise HTTPException(status_code=413, detail="Video exceeds configured semantic upload limit")

    now = datetime.now(timezone.utc)
    object_path = f"uploads/{now:%Y/%m/%d}/{uuid4().hex}{suffix}"
    try:
        signed = create_signed_upload(UPLOAD_BUCKET, object_path)
        asset = create_asset(
            object_path=object_path,
            bucket=UPLOAD_BUCKET,
            original_filename=payload.filename,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
            location_id=payload.location_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        **signed,
        "asset_id": asset["id"],
        "chunk_size": TUS_CHUNK_BYTES,
        "expires_in_seconds": 7200,
    }


@app.post("/api/v1/jobs")
def submit_semantic_job(payload: JobRequest) -> dict:
    _require_semantic()
    try:
        return queue_asset(payload.asset_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/v1/jobs/{job_id}")
def semantic_job_status(job_id: str) -> dict:
    _require_semantic()
    try:
        job = get_job(job_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/v1/selftest")
def selftest() -> dict:
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".avi") as tmp:
            tmp_path = tmp.name
        writer = cv2.VideoWriter(
            tmp_path,
            cv2.VideoWriter_fourcc(*"MJPG"),
            12.0,
            (320, 180),
        )
        if not writer.isOpened():
            raise RuntimeError("Synthetic video writer unavailable")
        for index in range(36):
            frame = np.zeros((180, 320, 3), dtype=np.uint8)
            x = 10 + index * 6
            cv2.rectangle(
                frame,
                (x, 65),
                (x + 45, 115),
                (255, 255, 255),
                -1,
            )
            writer.write(frame)
        writer.release()
        result = analyze_video(tmp_path, sample_every=1)
        result["selftest"] = "passed"
        result["persisted"] = False
        return result
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/api/v1/analyze")
async def analyze(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "upload.mp4").suffix.lower() or ".mp4"
    if suffix not in SUPPORTED_VIDEO_SUFFIXES:
        raise HTTPException(status_code=415, detail="Unsupported video format")

    max_bytes = 4 * 1024 * 1024
    written = 0
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            while chunk := await file.read(512 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail="Public demo accepts videos up to 4 MB. Full Engine uploads are available when enabled.",
                    )
                tmp.write(chunk)
        result = analyze_video(tmp_path, sample_every=4)
        result["filename"] = file.filename
        try:
            result["persisted"] = save_analysis(result, file.filename)
        except RuntimeError as exc:
            result["persisted"] = False
            result["persistence_error"] = str(exc)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
