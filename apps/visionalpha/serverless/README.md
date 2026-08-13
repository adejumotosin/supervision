# VisionAlpha Vercel Demo API

This directory contains the lightweight API used by the public VisionAlpha Vercel demo.

The canonical production computer-vision engine remains in `apps/visionalpha/backend` and uses Ultralytics plus Supervision. That full stack cannot fit in a Vercel Python Function because its deployed dependency bundle exceeds Vercel's function-size limit.

The Vercel demo therefore uses OpenCV motion segmentation plus lightweight centroid association to provide a real video-to-activity-index workflow for short public demo clips.

Public services:

- Dashboard: `https://visionalpha.vercel.app`
- Demo API: `https://visionalpha-api.vercel.app`
- Health: `/health`
- Historical activity series: `/api/v1/history`
- Synthetic pipeline check: `/api/v1/selftest`
- Video analysis: `POST /api/v1/analyze`

## Supabase persistence

When the following server-only environment variables are configured, completed analyses are persisted to Supabase and the overview/history endpoints use stored observations when available:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` or `SUPABASE_SERVICE_ROLE_KEY`

Do not expose a Supabase secret or service-role key to the frontend.

The public demo accepts video uploads up to 4 MB. For semantic vehicle, person, bus, truck and boat detection, deploy `apps/visionalpha/backend` to a container or GPU-capable platform.
