from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .pipeline import analyze_video

app = FastAPI(title="VisionAlpha API", version="0.1.0")

origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "visionalpha-api"}


@app.get("/api/v1/overview")
def overview() -> dict:
    return {
        "economic_activity_index": 82.41,
        "change_30d": 3.82,
        "regime": "economic_expansion",
        "signal": {"name": "Nigeria Industrial Activity", "direction": "bullish", "confidence": 0.87},
        "mode": "seeded_demo",
    }


@app.post("/api/v1/analyze")
async def analyze(file: UploadFile = File(...)) -> dict:
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

        result = analyze_video(tmp_path, sample_every=int(os.getenv("SAMPLE_EVERY", "3")))
        result["filename"] = file.filename
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
