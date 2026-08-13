from __future__ import annotations

import json
import os
from typing import Any

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def configuration() -> dict[str, str] | None:
    project_id = os.getenv("GCP_PROJECT_ID", "").strip()
    region = os.getenv("GCP_REGION", "").strip()
    job_name = os.getenv("GCP_WORKER_JOB", "").strip()
    service_account_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON", "").strip()
    if not all((project_id, region, job_name, service_account_json)):
        return None
    return {
        "project_id": project_id,
        "region": region,
        "job_name": job_name,
        "service_account_json": service_account_json,
    }


def is_configured() -> bool:
    return configuration() is not None


def trigger_worker_job() -> dict[str, Any]:
    configured = configuration()
    if configured is None:
        raise RuntimeError("Google Cloud worker trigger is not configured")

    try:
        info = json.loads(configured["service_account_json"])
    except json.JSONDecodeError as exc:
        raise RuntimeError("GCP_SERVICE_ACCOUNT_JSON is not valid JSON") from exc

    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=[CLOUD_PLATFORM_SCOPE],
    )
    session = AuthorizedSession(credentials)
    endpoint = (
        "https://run.googleapis.com/v2/projects/"
        f"{configured['project_id']}/locations/{configured['region']}/"
        f"jobs/{configured['job_name']}:run"
    )
    response = session.post(endpoint, json={}, timeout=15)
    if response.status_code >= 400:
        raise RuntimeError(
            f"Cloud Run job trigger failed ({response.status_code}): {response.text[:1000]}"
        )
    payload = response.json()
    return payload if isinstance(payload, dict) else {"status": "accepted"}
