FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE.md /workspace/
COPY src /workspace/src
RUN pip install --no-cache-dir -e .

COPY apps/visionalpha/backend/requirements.txt /workspace/apps/visionalpha/backend/requirements.txt
RUN pip install --no-cache-dir -r /workspace/apps/visionalpha/backend/requirements.txt

COPY apps/visionalpha/backend /workspace/apps/visionalpha/backend
RUN touch /workspace/apps/__init__.py /workspace/apps/visionalpha/__init__.py \
    && chmod +x /workspace/apps/visionalpha/backend/entrypoint.sh

ENTRYPOINT ["/workspace/apps/visionalpha/backend/entrypoint.sh"]
