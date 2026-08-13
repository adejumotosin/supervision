# VisionAlpha Frontend Deployment

The production dashboard is deployed from this directory on Vercel.

- Production branch: `develop`
- Root directory: `apps/visionalpha/frontend`
- API environment variable: `NEXT_PUBLIC_VISIONALPHA_API_URL`

The dashboard reads persisted activity history from the VisionAlpha API when observations exist and falls back to seeded research data when the history store is empty.
