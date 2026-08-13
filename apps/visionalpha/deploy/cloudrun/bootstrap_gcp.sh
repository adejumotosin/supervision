#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="strategic-well-477307-p7"
REGION="europe-west1"
REPOSITORY="visionalpha"

printf 'Configuring Google Cloud project %s\n' "$PROJECT_ID"
gcloud config set project "$PROJECT_ID"
gcloud config set run/region "$REGION"

printf 'Enabling required Google Cloud APIs...\n'
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iamcredentials.googleapis.com

if gcloud artifacts repositories describe "$REPOSITORY" --location="$REGION" >/dev/null 2>&1; then
  printf 'Artifact Registry repository %s already exists in %s.\n' "$REPOSITORY" "$REGION"
else
  printf 'Creating Artifact Registry repository %s in %s...\n' "$REPOSITORY" "$REGION"
  gcloud artifacts repositories create "$REPOSITORY" \
    --repository-format=docker \
    --location="$REGION" \
    --description="VisionAlpha container images"
fi

printf '\nBootstrap complete.\n'
printf 'Next: create the Secret Manager secret visionalpha-supabase-secret, then build the GPU image.\n'
