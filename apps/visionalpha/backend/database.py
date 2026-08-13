from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def credentials() -> tuple[str, str] | None:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.getenv("SUPABASE_SECRET_KEY", "").strip()
    )
    if not url or not key:
        return None
    return url, key


def is_configured() -> bool:
    return credentials() is not None


def request(method: str, resource: str, payload: dict[str, Any] | None = None) -> Any:
    configured = credentials()
    if configured is None:
        raise RuntimeError("Supabase persistence is not configured")

    base_url, key = configured
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(
        f"{base_url}/rest/v1/{resource}",
        data=body,
        method=method,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Prefer": "return=representation",
        },
    )
    try:
        with urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase request failed ({exc.code}): {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Supabase request failed: {exc}") from exc


def create_asset(
    *,
    object_path: str,
    bucket: str = "visionalpha-video",
    original_filename: str | None = None,
    content_type: str | None = None,
    size_bytes: int | None = None,
    location_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "object_path": object_path,
        "bucket": bucket,
        "original_filename": original_filename,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "location_id": location_id,
        "metadata": metadata or {},
    }
    rows = request("POST", "video_assets", payload)
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("Supabase did not return the created asset")
    return rows[0]


def create_job(asset_id: str, engine: str = "yolo_supervision") -> dict[str, Any]:
    payload = {"asset_id": asset_id, "engine": engine, "status": "queued"}
    rows = request("POST", "processing_jobs", payload)
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("Supabase did not return the created job")
    request("PATCH", f"video_assets?id=eq.{quote(asset_id)}", {"status": "queued"})
    return rows[0]


def get_job(job_id: str) -> dict[str, Any] | None:
    rows = request(
        "GET",
        f"processing_jobs?id=eq.{quote(job_id)}&select=*&limit=1",
    )
    return rows[0] if isinstance(rows, list) and rows else None


def claim_next_job(worker_id: str) -> dict[str, Any] | None:
    rows = request("POST", "rpc/claim_visionalpha_job", {"p_worker_id": worker_id})
    return rows[0] if isinstance(rows, list) and rows else None


def get_asset(asset_id: str) -> dict[str, Any] | None:
    rows = request(
        "GET",
        f"video_assets?id=eq.{quote(asset_id)}&select=*&limit=1",
    )
    return rows[0] if isinstance(rows, list) and rows else None


def update_asset(asset_id: str, **fields: Any) -> None:
    request("PATCH", f"video_assets?id=eq.{quote(asset_id)}", fields)


def update_job(job_id: str, **fields: Any) -> None:
    request("PATCH", f"processing_jobs?id=eq.{quote(job_id)}", fields)


def save_analysis_result(
    result: dict[str, Any],
    *,
    asset: dict[str, Any],
    job_id: str,
) -> dict[str, Any]:
    payload = {
        "location_id": asset.get("location_id"),
        "asset_id": asset.get("id"),
        "job_id": job_id,
        "filename": asset.get("original_filename"),
        "source_mode": result.get("engine", "yolo_supervision"),
        "frames_total": result.get("frames_total", 0),
        "frames_processed": result.get("frames_processed", 0),
        "unique_tracks": result.get("unique_tracks", 0),
        "activity_index": result.get("activity_index"),
        "counts": result.get("counts", {}),
        "feature_scores": result.get("feature_scores", {}),
        "duration_seconds": result.get("duration_seconds"),
        "sample_every": result.get("sample_every"),
        "rates_per_minute": result.get("rates_per_minute", {}),
        "domain_indices": result.get("domain_indices", {}),
        "engine_version": result.get("engine_version"),
        "metadata": {
            "methodology": result.get("methodology"),
            "raw_detections": result.get("raw_detections", {}),
            "domain_feature_scores": result.get("domain_feature_scores", {}),
        },
    }
    rows = request("POST", "analysis_runs", payload)
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("Supabase did not return the saved analysis")
    return rows[0]
