#!/bin/sh
set -eu

if [ "${VISIONALPHA_ROLE:-api}" = "worker" ]; then
  exec python -m apps.visionalpha.backend.worker
fi

exec uvicorn apps.visionalpha.backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
