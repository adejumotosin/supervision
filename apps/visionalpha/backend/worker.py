from __future__ import annotations

import os
import socket
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from .database import (
    claim_next_job,
    get_asset,
    save_analysis_result,
    update_asset,
    update_job,
)
from .pipeline import analyze_video
from .storage import download_supabase_object


def _worker_id() -> str:
    return os.getenv("WORKER_ID", "").strip() or socket.gethostname()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _one_shot() -> bool:
    return os.getenv("WORKER_ONCE", "0").strip() == "1"


def process_one_job() -> bool:
    worker_id = _worker_id()
    job = claim_next_job(worker_id)
    if not job:
        return False

    job_id = str(job["id"])
    asset_id = str(job["asset_id"])
    asset = get_asset(asset_id)
    if asset is None:
        update_job(job_id, status="failed", error="Video asset not found", progress=100, completed_at=_now())
        return True

    suffix = Path(asset.get("original_filename") or asset.get("object_path") or "video.mp4").suffix or ".mp4"
    tmp_path = None

    try:
        update_asset(asset_id, status="processing")
        update_job(job_id, progress=5)

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name

        download_supabase_object(
            str(asset.get("bucket") or "visionalpha-video"),
            str(asset["object_path"]),
            tmp_path,
        )
        update_job(job_id, progress=15)

        result = analyze_video(
            tmp_path,
            sample_every=int(os.getenv("SAMPLE_EVERY", "3")),
            confidence=float(os.getenv("VISION_CONFIDENCE", "0.35")),
        )
        update_job(job_id, progress=90)

        analysis = save_analysis_result(result, asset=asset, job_id=job_id)
        update_job(
            job_id,
            status="succeeded",
            progress=100,
            analysis_run_id=analysis.get("id"),
            completed_at=_now(),
            error=None,
        )
        update_asset(
            asset_id,
            status="processed",
            duration_seconds=result.get("duration_seconds"),
        )
        return True
    except Exception as exc:
        attempts = int(job.get("attempts") or 1)
        max_attempts = int(job.get("max_attempts") or 3)
        message = str(exc)[:4000]

        if attempts < max_attempts:
            update_job(
                job_id,
                status="queued",
                progress=0,
                worker_id=None,
                started_at=None,
                error=message,
            )
            update_asset(asset_id, status="queued")
            if _one_shot():
                raise RuntimeError(message) from exc
        else:
            update_job(
                job_id,
                status="failed",
                progress=100,
                error=message,
                completed_at=_now(),
            )
            update_asset(asset_id, status="failed")
        return True
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def run_worker() -> None:
    poll_seconds = max(1.0, float(os.getenv("WORKER_POLL_SECONDS", "5")))
    once = _one_shot()

    while True:
        processed = process_one_job()
        if once:
            return
        if not processed:
            time.sleep(poll_seconds)


if __name__ == "__main__":
    run_worker()
