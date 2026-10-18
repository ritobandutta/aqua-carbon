#!/usr/bin/env bash
# Deploy AquaCarbon DC to Google Cloud Run
# Mandatory submission requirements from Organizer Q&A:
# 1. Cloud Run deployment with public unauthenticated URL for judges
# 2. Downscaled to zero min-instances (--min-instances=0) to prevent idle costs
# 3. Fast boot (<1s) and parameterizable secrets via GCP Secret Manager

PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="aquacarbon-dc"
REGION="us-central1"

echo "Deploying ${SERVICE_NAME} to Google Cloud Run in ${REGION} (Project: ${PROJECT_ID})..."

gcloud run deploy ${SERVICE_NAME} \
  --source . \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 5 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 120s \
  --port 8080

echo "Deployment complete! Verify the deployed service URL with:"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'
