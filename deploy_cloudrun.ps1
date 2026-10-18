# PowerShell Deployment Script for Google Cloud Run
# AquaCarbon DC — Commons Edition (v2)

$ServiceName = "aquacarbon-dc"
$Region = "us-central1"

Write-Host "Deploying $ServiceName to Google Cloud Run in $Region..." -ForegroundColor Cyan

gcloud run deploy $ServiceName `
  --source . `
  --region $Region `
  --platform managed `
  --allow-unauthenticated `
  --min-instances 0 `
  --max-instances 5 `
  --memory 512Mi `
  --cpu 1 `
  --timeout 120s `
  --port 8080

Write-Host "Deployment complete! Checking Service URL..." -ForegroundColor Green
gcloud run services describe $ServiceName --region $Region --format "value(status.url)"
