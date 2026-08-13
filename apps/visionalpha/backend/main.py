from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .database import create_asset, create_job, get_job, is_configured
from .pipeline import ENGINE_VERSION, analyze_video

app = FastAPI(title="VisionAlpha API", version="0.3.0")

origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AssetRegistration(BaseModel):
    object_path: str = Field(min_length=1)
    bucket: str = Field(default="visionalpha-video", min_length=1)
    original_filename: str | None = None
    content_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    location_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobSubmission(BaseModel):
    asset_id: str = Field(min_length=1)
    engine: str = Field(default="yolo_supervision", min_length=1)


def _require_persistence() -> None:
    if not is_configured():
        raise HTTPException(status_code=503, detail="Supabase persistence is not configured")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "visionalpha-api",
        "engine": "yolo_supervision",
        "engine_version": ENGINE_VERSION,
        "queue": "supabase" if is_configured() else "unconfigured",
    }


@app.get("/api/v1/methodology")
def methodology() -> dict:
    return {
        "engine": "YOLO + Supervision ByteTrack",
        "normalization": "Unique tracks are converted to per-minute rates before baseline comparison.",
        "domains": {
            "economic_activity": ["person", "car", "motorcycle", "bus", "truck", "boat"],
            "port_logistics": ["truck", "boat", "car", "bus"],
        },
        "baseline_status": "provisional",
        "required_calibration": ["location", "camera", "hour", "weekday", "season"],
    }


@app.get("/api/v1/overview")
def overview() -> dict:
    return {
        "economic_activity_index": 82.41,
        "change_30d": 3.82,
        "regime": "economic_expansion",
        "signal": {"name": "Nigeria Industrial Activity", "direction": "bullish", "confidence": 0.87},
        "mode": "seeded_demo",
    }


@app.post("/api/v1/assets")
def register_asset(payload: AssetRegistration) -> dict:
    _require_persistence()
    try:
        return create_asset(**payload.model_dump())
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/v1/jobs")
def submit_job(payload: JobSubmission) -> dict:
    _require_persistence()
    try:
        return create_job(payload.asset_id, payload.engine)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/v1/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    _require_persistence()
    try:
        job = get_job(job_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/api/v1/analyze")
async def analyze(file: UploadFile = File(...)) -> dict:
    """Direct analysis route for local/container testing and short trusted uploads."""
    suffix = Path(file.filename or "upload.mp4").suffix.lower() or ".mp4"
    if suffix not in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        raise HTTPException(status_code=415, detail="Unsupported video format")

    max_bytes = int(os.getenv("MAX_UPLOAD_BYTES", str(250 * 1024 * 1024)))
    written = 0
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(status_code=413, detail="Video exceeds configured upload limit")
                tmp.write(chunk)

        result = analyze_video(
            tmp_path,
            sample_every=int(os.getenv("SAMPLE_EVERY", "3")),
            confidence=float(os.getenv("VISION_CONFIDENCE", "0.35")),
        )
        result["filename"] = file.filename
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
