from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .database import credentials


def download_supabase_object(bucket: str, object_path: str, destination: str | Path) -> Path:
    configured = credentials()
    if configured is None:
        raise RuntimeError("Supabase storage is not configured")

    base_url, key = configured
    bucket_part = quote(bucket, safe="")
    object_part = quote(object_path.lstrip("/"), safe="/")
    request = Request(
        f"{base_url}/storage/v1/object/{bucket_part}/{object_part}",
        method="GET",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
        },
    )

    target = Path(destination)
    try:
        with urlopen(request, timeout=60) as response, target.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Storage download failed ({exc.code}): {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Storage download failed: {exc}") from exc

    return target
