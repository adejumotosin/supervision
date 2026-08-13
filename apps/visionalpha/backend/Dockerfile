FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE.md /workspace/
COPY supervision /workspace/supervision
RUN pip install --no-cache-dir -e .

COPY apps/visionalpha/backend/requirements.txt /workspace/apps/visionalpha/backend/requirements.txt
RUN pip install --no-cache-dir -r /workspace/apps/visionalpha/backend/requirements.txt

COPY apps/visionalpha/backend /workspace/apps/visionalpha/backend
CMD ["uvicorn", "apps.visionalpha.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
