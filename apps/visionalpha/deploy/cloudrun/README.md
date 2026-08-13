# VisionAlpha Cloud Run GPU Job

This deployment runs the VisionAlpha YOLO + Supervision semantic worker as an on-demand Google Cloud Run Job.

The public dashboard and coordination API remain on Vercel. Video bytes live in Supabase Storage. Each semantic submission creates a Supabase queue item and the coordination API starts this Cloud Run Job. The job claims one queue item, processes it, persists the result, and exits.

## Target configuration

- Region: `europe-west1`
- GPU: NVIDIA L4
- GPU count: 1
- CPU: 4
- Memory: 16 GiB
- Tasks: 1
- Parallelism: 1
- Job timeout: 3600 seconds
- Worker mode: one queue item per execution

## 1. Select a Google Cloud project

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud config set run/region europe-west1
```

Billing must be enabled on the selected project.

## 2. Enable APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

## 3. Create Artifact Registry

```bash
gcloud artifacts repositories create visionalpha \
  --repository-format=docker \
  --location=europe-west1 \
  --description="VisionAlpha container images"
```

If the repository already exists, skip this command.

## 4. Store the Supabase server secret

Create a Secret Manager secret named:

```text
visionalpha-supabase-secret
```

Store the VisionAlpha Supabase server secret as its latest version. Do not commit the value to GitHub.

The runtime service account used by the Cloud Run Job must have permission to access this secret.

## 5. Build the CUDA worker image

From the repository root:

```bash
gcloud builds submit . \
  --config apps/visionalpha/deploy/cloudrun/cloudbuild.yaml
```

The default image is:

```text
europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/visionalpha/visionalpha-worker:latest
```

The GPU Dockerfile installs a CUDA 12.1 PyTorch build and preloads `yolo11n.pt` into the image.

## 6. Deploy the GPU job

```bash
gcloud run jobs deploy visionalpha-semantic-worker \
  --image europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/visionalpha/visionalpha-worker:latest \
  --region europe-west1 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --no-gpu-zonal-redundancy \
  --cpu 4 \
  --memory 16Gi \
  --tasks 1 \
  --parallelism 1 \
  --task-timeout 3600s \
  --max-retries 0 \
  --set-env-vars VISIONALPHA_ROLE=worker,WORKER_ONCE=1,SAMPLE_EVERY=3,VISION_CONFIDENCE=0.35,VISION_MODEL=yolo11n.pt,SUPABASE_URL=https://vqndwsvticfrsaecjlhl.supabase.co \
  --set-secrets SUPABASE_SECRET_KEY=visionalpha-supabase-secret:latest
```

The application has its own queue retry policy. Cloud Run task retries are therefore disabled to avoid two independent retry systems retrying the same failed work.

## 7. Test the job manually

After one semantic job exists in `public.processing_jobs` with status `queued`:

```bash
gcloud run jobs execute visionalpha-semantic-worker \
  --region europe-west1 \
  --wait
```

A successful run should:

1. claim a queued job
2. download the source video from the private `visionalpha-video` bucket
3. run YOLO + Supervision tracking
4. calculate per-minute activity rates
5. calculate Economic Activity and Port & Logistics indices
6. insert an `analysis_runs` row
7. mark the processing job `succeeded`

## 8. Create the Vercel trigger identity

Create a dedicated Google Cloud service account for the Vercel coordination API. Grant it only the ability to invoke `visionalpha-semantic-worker`.

The Vercel `visionalpha-api` project will need these production variables:

```text
GCP_PROJECT_ID=YOUR_PROJECT_ID
GCP_REGION=europe-west1
GCP_WORKER_JOB=visionalpha-semantic-worker
GCP_SERVICE_ACCOUNT_JSON=<server-only service account JSON>
```

Keep `GCP_SERVICE_ACCOUNT_JSON` marked sensitive in Vercel and never expose it to the frontend.

After the trigger is verified, set:

```text
ENABLE_SEMANTIC_UPLOADS=1
```

Until then, leave it at `0`. The dashboard will show `Full Engine Soon` and continue offering the Quick Test path.

## Production hardening after first end-to-end run

- replace the long-lived service-account JSON with workload identity federation
- calibrate baselines by site, camera, hour, weekday and season
- add data-quality and camera-drift checks
- migrate away from the deprecated in-package Supervision ByteTrack interface when the tracker migration is finalized
- add specialized port/container detection models
- add line crossing, dwell time, queue length and direction-specific flows
