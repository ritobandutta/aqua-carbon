# Deployment Guide (Google Cloud)

Status: **skeleton**. Nothing is deployed and nothing here has been run. Each phase of the build adds the matching section. All project, account and billing specifics are placeholders. Deployment happens from a personal GCP account, never company infrastructure.

Placeholders used below: `<PROJECT_ID>`, `<REGION>`, `<ARTIFACT_REPO>`, `<DATASET>`.

## 0. Prerequisites

- [ ] A personal GCP project with billing and a budget alert set
- [ ] `gcloud` installed and authenticated on the deploying machine
- [ ] Decision on who deploys (see `OPEN_QUESTIONS.md`)

## 1. Project setup checklist

- [ ] Enable APIs: Vertex AI, Cloud Run, Artifact Registry, BigQuery, Secret Manager, Cloud Build, IAM
- [ ] Create an Artifact Registry repo `<ARTIFACT_REPO>` in `<REGION>`
- [ ] Create one service account per service with least privilege:
  - api: Vertex AI user, BigQuery data editor on `<DATASET>`, Secret Manager accessor, Cloud Run invoker for engine-mcp, verifier, community
  - engine-mcp: no data access beyond its own needs
  - verifier: Vertex AI user only, no BigQuery access
  - community: read access to the datasets it uses
- [ ] Create the BigQuery dataset `<DATASET>` (DDL will live in `infra/bigquery/`)

## 2. Configuration

| Variable | Local | Cloud |
|---|---|---|
| `GOOGLE_GENAI_USE_VERTEXAI` | `false` | `true` |
| `GOOGLE_API_KEY` | AI Studio key in `.env` | not used |
| `GOOGLE_CLOUD_PROJECT` | unset | `<PROJECT_ID>` |
| `GOOGLE_CLOUD_LOCATION` | unset | `<REGION>` |
| `STORE_BACKEND` | `duckdb` | `bigquery` |
| `BIGQUERY_DATASET` | unset | `<DATASET>` |
| service URLs | localhost ports | Cloud Run URLs |

Secrets go in Secret Manager and are mounted as env vars. Never bake them into images.

## 3. Services (filled in as built)

| Service | Cloud Run name | Public? | Notes |
|---|---|---|---|
| api | `aquacarbon-api` | via web only | calls the others with service-to-service IAM |
| engine-mcp | `aquacarbon-engine-mcp` | no | authenticated invoker only |
| verifier | `aquacarbon-verifier` | no | separate service account, trust boundary |
| community | `aquacarbon-community` | no | authenticated invoker only |
| web | Firebase Hosting or Cloud Run | yes | decision pending |

Build and deploy commands are added per service when its Dockerfile exists. Until then this table is intent, not fact.

## 4. A2A and service-to-service auth

- Verifier and community services require authenticated callers (Cloud Run IAM, ID tokens).
- Only the api service account has `run.invoker` on them.
- Service URLs are injected into the api as `VERIFIER_A2A_URL` and `COMMUNITY_A2A_URL`.

## 5. Cost guardrails

- Budget alert on the project, with a hard monthly cap you are comfortable with.
- Cloud Run `min-instances=0` and a conservative `max-instances`.
- Route cheap steps to Flash and reserve Pro for planning and the brief.
- Cache engine runs by `run_id`, since identical inputs give identical results.
- Report inference cost and latency per scenario in the eval report.

## 6. Verify a deployment

- [ ] `GET /health` on each service
- [ ] Run the seeded demo scenario end to end from the deployed web app
- [ ] Confirm the verifier is called and that a deliberately wrong number gets blocked
- [ ] Confirm no secret appears in logs or the image

## 7. Teardown

- [ ] Delete Cloud Run services, the Artifact Registry repo, the BigQuery dataset and secrets
- [ ] Remove service accounts
- [ ] Delete the project, or confirm the budget alert is still armed

## 8. Known gaps

Fill in as discovered: quotas, region availability of models, cold-start behaviour.
