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


def _request(method: str, resource: str, payload: dict[str, Any] | None = None) -> Any:
    configured = credentials()
    if configured is None:
        raise RuntimeError("Supabase persistence is not configured")

    base_url, key = configured
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
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
        with urlopen(request, timeout=12) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase request failed ({exc.code}): {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Supabase request failed: {exc}") from exc


def save_analysis(result: dict[str, Any], filename: str | None) -> bool:
    if not is_configured():
        return False

    payload = {
        "filename": filename,
        "source_mode": result.get("mode", "serverless_motion_proxy"),
        "frames_total": result.get("frames_total", 0),
        "frames_processed": result.get("frames_processed", 0),
        "unique_tracks": result.get("unique_tracks", 0),
        "activity_index": result.get("activity_index"),
        "counts": result.get("counts", {}),
        "feature_scores": result.get("feature_scores", {}),
        "avg_motion_ratio": result.get("avg_motion_ratio"),
        "metadata": {"methodology": result.get("methodology")},
    }
    _request("POST", "analysis_runs", payload)
    return True


def get_history(limit: int = 30) -> list[dict[str, Any]]:
    if not is_configured():
        return []

    limit = max(1, min(int(limit), 100))
    columns = (
        "id,created_at,filename,source_mode,frames_processed,unique_tracks,"
        "activity_index,counts,feature_scores,avg_motion_ratio,duration_seconds,"
        "rates_per_minute,domain_indices,engine_version"
    )
    rows = _request(
        "GET",
        f"analysis_runs?select={columns}&order=created_at.desc&limit={limit}",
    )
    if not isinstance(rows, list):
        return []
    rows.reverse()
    return rows


def create_asset(
    *,
    object_path: str,
    bucket: str,
    original_filename: str | None,
    content_type: str | None,
    size_bytes: int | None,
    location_id: str | None = None,
) -> dict[str, Any]:
    payload = {
        "object_path": object_path,
        "bucket": bucket,
        "original_filename": original_filename,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "location_id": location_id,
        "status": "pending_upload",
    }
    rows = _request("POST", "video_assets", payload)
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("Supabase did not return the created asset")
    return rows[0]


def queue_asset(asset_id: str) -> dict[str, Any]:
    rows = _request(
        "POST",
        "processing_jobs",
        {"asset_id": asset_id, "engine": "yolo_supervision", "status": "queued"},
    )
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("Supabase did not return the created job")
    _request("PATCH", f"video_assets?id=eq.{quote(asset_id)}", {"status": "queued"})
    return rows[0]


def get_job(job_id: str) -> dict[str, Any] | None:
    rows = _request(
        "GET",
        f"processing_jobs?id=eq.{quote(job_id)}&select=*&limit=1",
    )
    return rows[0] if isinstance(rows, list) and rows else None
