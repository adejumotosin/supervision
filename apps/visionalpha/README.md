# VisionAlpha

VisionAlpha is an alternative-data investment intelligence engine that turns video into measurable economic activity signals.

It uses object detection plus Supervision tracking to convert footage from roads, ports, stores, construction sites, and industrial locations into standardized activity indices that can be compared with financial and macroeconomic data.

## Architecture

```text
Browser
  |
  | quick clips
  v
Vercel demo API -> OpenCV motion proxy -> Supabase history

Browser
  |
  | Full Engine upload
  v
Supabase Storage (TUS resumable upload)
  |
  v
video_assets + processing_jobs
  |
  v
Container / GPU worker
  |
  v
YOLO -> Supervision ByteTrack -> per-minute object rates
  |
  v
Economic Activity Index + Port & Logistics Index
  |
  v
analysis_runs -> dashboard history
```

## Current public demo

- Next.js finance dashboard
- Vercel OpenCV motion-analysis proxy
- Supabase persistence
- Historical activity chart
- Quick video upload up to 4 MB

Public demo services:

- Dashboard: `https://visionalpha.vercel.app`
- API: `https://visionalpha-api.vercel.app`

## Phase 3 Full Engine

Phase 3 adds the production semantic path without removing the public demo.

### Semantic computer vision

The canonical backend uses Ultralytics YOLO plus Supervision ByteTrack to detect and track:

- people
- cars
- motorcycles
- buses
- trucks
- boats

Raw unique-track counts are normalized into per-minute rates before baseline comparison. This avoids treating clips with different durations as directly comparable.

### Port & Logistics vertical

The first specialized domain index combines truck, boat, car and bus activity. Truck and boat activity receive the largest weights because they are the most direct current proxies for freight and port throughput in the generic COCO model.

The default baselines remain provisional. A research-quality deployment must calibrate them by location, camera, hour, weekday and season.

### Large video uploads

Full Engine footage is uploaded directly from the browser to the private `visionalpha-video` Supabase Storage bucket using resumable TUS uploads. The Vercel API only signs the upload and creates job metadata, so large video bytes do not pass through a Vercel function.

### Processing queue

Phase 3 adds:

- `video_assets`
- `processing_jobs`
- richer `analysis_runs` fields
- atomic job claiming with `claim_visionalpha_job()`
- asset and job status tracking
- a worker that downloads footage, runs semantic analysis and persists results

## Run the frontend

```bash
cd apps/visionalpha/frontend
npm install
npm run dev
```

Create `.env.local` from `.env.example`.

## Run the Full Engine API

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r apps/visionalpha/backend/requirements.txt
uvicorn apps.visionalpha.backend.main:app --reload --port 8000
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Run the worker

```bash
python -m apps.visionalpha.backend.worker
```

Or use the same Docker image with:

```text
VISIONALPHA_ROLE=worker
```

The default container role is `api`.

## Full Engine API

- `GET /health`
- `GET /api/v1/methodology`
- `POST /api/v1/assets`
- `POST /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `POST /api/v1/analyze` for direct trusted/container testing

The Vercel coordination API additionally exposes:

- `POST /api/v1/uploads/sign`
- `POST /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`

## Environment

The Full Engine expects:

```text
CORS_ORIGINS=https://visionalpha.vercel.app
VISION_MODEL=yolo11n.pt
VISION_CONFIDENCE=0.35
SAMPLE_EVERY=3
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=server-only-secret
VISIONALPHA_ROLE=api
```

For a worker deployment set:

```text
VISIONALPHA_ROLE=worker
```

Never expose the Supabase secret key to the browser.

## Deployment

Frontend and coordination API can remain on Vercel.

The YOLO plus Supervision backend and worker require a container-capable service. CPU can support development and short clips, while a GPU worker is preferable for sustained or high-volume video processing.

The backend Docker build context must be the repository root and the Dockerfile is:

```text
apps/visionalpha/backend/Dockerfile
```

## Research safeguards

VisionAlpha indices are alternative-data research features, not automatically valid investment signals. Before using them for portfolio decisions, the system still needs:

1. camera and location-specific baseline calibration
2. zone and directional line-crossing metrics
3. dwell-time and queue measurement
4. higher-quality port and container detection models
5. macro and market time-series joins
6. out-of-sample factor backtests
7. confidence and data-quality scoring
8. monitoring for camera drift, occlusion and regime changes
