# VisionAlpha

VisionAlpha is an alternative-data investment intelligence engine that turns video into measurable economic activity signals.

It uses object detection plus Supervision tracking to convert footage from roads, ports, stores, construction sites, and industrial locations into standardized activity indices that can be compared with financial and macroeconomic data.

## MVP architecture

```text
Video / CCTV / uploaded file
        |
        v
Ultralytics detector
        |
        v
Supervision detections + ByteTrack
        |
        v
Object / flow / activity metrics
        |
        v
FastAPI analytics service
        |
        v
Alternative Data Indices
        |
        v
Next.js investment dashboard
```

## Included

- Bloomberg-inspired Next.js dashboard
- Economic Activity Index and domain indices
- Transport, ports, retail, construction, industrial signal cards
- Transparent baseline-relative index methodology
- Video upload workflow
- FastAPI analysis endpoint
- Ultralytics object detection
- Supervision ByteTrack tracking
- Demo mode for instant dashboard use
- Docker-ready backend

## Run the frontend

```bash
cd apps/visionalpha/frontend
npm install
npm run dev
```

Create `.env.local` from `.env.example`. The dashboard works in seeded demo mode even when the backend is not running.

## Run the backend

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r apps/visionalpha/backend/requirements.txt
uvicorn apps.visionalpha.backend.main:app --reload --port 8000
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## API

- `GET /health`
- `GET /api/v1/overview`
- `POST /api/v1/analyze` with a video file

## Index methodology

VisionAlpha does not pretend raw object counts are immediately investable signals. Each measured feature is compared with a configurable historical baseline, transformed to a bounded 0 to 100 score, and then combined into domain-level indices. Production deployments should estimate baselines by camera, location, hour, weekday, season, and asset universe.

## Deployment

Frontend: Vercel, root directory `apps/visionalpha/frontend`.

Backend: Railway, Render, Fly.io, AWS, GCP, or another container/GPU service. Computer-vision inference should not be placed in a short-lived Vercel serverless function.

## Next production milestones

1. Persist observations in Postgres/Supabase.
2. Add camera/location registry and historical baselines.
3. Add polygon zones and directional line crossing.
4. Add calibrated vehicle speed and dwell-time estimation.
5. Add port/container and construction-specific detection models.
6. Join CV indices to market and macro time series.
7. Backtest signal efficacy and publish factor diagnostics.
8. Add live RTSP ingestion and scheduled processing.
