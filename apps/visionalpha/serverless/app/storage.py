from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

from .database import credentials


def create_signed_upload(bucket: str, object_path: str) -> dict[str, str]:
    configured = credentials()
    if configured is None:
        raise RuntimeError("Supabase storage is not configured")

    base_url, key = configured
    bucket_part = quote(bucket, safe="")
    object_part = quote(object_path.lstrip("/"), safe="/")
    endpoint = f"{base_url}/storage/v1/object/upload/sign/{bucket_part}/{object_part}"
    request = Request(
        endpoint,
        data=b"{}",
        method="POST",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-upsert": "false",
        },
    )

    try:
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Signed upload request failed ({exc.code}): {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Signed upload request failed: {exc}") from exc

    relative_url = str(payload.get("url") or "")
    if not relative_url:
        raise RuntimeError("Supabase did not return a signed upload URL")

    if relative_url.startswith("http://") or relative_url.startswith("https://"):
        signed_url = relative_url
    elif relative_url.startswith("/"):
        signed_url = f"{base_url}/storage/v1{relative_url}"
    else:
        signed_url = f"{base_url}/storage/v1/{relative_url}"

    token = parse_qs(urlparse(signed_url).query).get("token", [""])[0]
    if not token:
        raise RuntimeError("Supabase signed upload response did not include a token")

    hostname = urlparse(base_url).hostname or ""
    project_ref = hostname.split(".", 1)[0]
    if not project_ref:
        raise RuntimeError("Unable to derive Supabase project reference")

    return {
        "token": token,
        "signed_url": signed_url,
        "tus_endpoint": f"https://{project_ref}.storage.supabase.co/storage/v1/upload/resumable",
        "bucket": bucket,
        "object_path": object_path,
    }
