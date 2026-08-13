from __future__ import annotations

import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .database import get_history, is_configured, save_analysis
from .pipeline import analyze_video

app = FastAPI(title="VisionAlpha API", version="0.2.0")
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


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "visionalpha-api",
        "mode": "serverless_motion_proxy",
        "persistence": "supabase" if is_configured() else "unconfigured",
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
    if suffix not in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
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
                        detail="Public demo accepts videos up to 4 MB",
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
