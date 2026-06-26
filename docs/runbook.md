# Demo Runbook (for the screen recording)

A 3–5 minute walkthrough covering **setup → usage → architecture**. Follow it
top to bottom while recording.

## 0. Pre-flight (off camera)
```bash
cp .env.example .env
# Optional fast path (no model download): set CLASSIFIER_STUB=1 in .env
docker compose pull           # optional
```

## 1. Setup (show the stack coming up)
```bash
docker compose up --build
# (GPU:)  docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
docker compose ps             # show all services healthy
```
Talking points: 6 services, two microservices (`webapp`, `classifier`) + worker
+ Postgres/Redis/MinIO, all on custom 47xxx ports.

## 2. User journey
1. Open **http://localhost:47080** → click **Register**; fill in account +
   **profile** (name, age, place of living, gender, country of origin,
   description) in one onboarding step.
2. Land on **My submissions** → **New submission** — note it asks **only for a
   photo**; the profile metadata (shown on the page) is attached automatically.
   (Optional: open **My profile** to show the metadata is editable.)
3. Choose a photo, **Submit**.
4. On the detail page, watch the **classification result appear live** (HTMX
   polling: `pending → done`). Point out age/gender predictions + NSFW safety.

Talking points: profile captured at onboarding and snapshotted onto each
submission; upload is validated, EXIF-stripped, stored in MinIO; metadata in
Postgres; classification runs **async** in the worker against the GPU service.

## 3. Admin panel
1. Logout, login as **admin@example.com / admin12345**.
2. Open **Admin panel**.
3. Filter live by **gender**, **age range**, **location**, **country**, free-text
   **search** — the table updates via HTMX without a reload.
4. Open a record: metadata, **photo reference** (presigned URL), classification
   result, timestamps.

## 4. API & docs
1. Open **http://localhost:47080/api/docs/** (Swagger).
2. Show `POST /api/submissions`, the admin filter endpoint, and the JWT auth
   endpoints.
3. (Optional) show **MinIO console** at http://localhost:47901 — the stored
   object; and `/metrics` for observability.

## 5. Architecture (slide / diagram)
Open [architecture.drawio](architecture.drawio) (draw.io) or the Mermaid diagram
in the [README](../README.md). Walk the request flow:
**browser → webapp (validate/store) → Redis → worker → classifier(GPU) → result
→ HTMX poll**. Mention Postgres indexing, safety rules, K8s/CI-CD.

## 6. CI/CD & Kubernetes (talk over the files)
- [.github/workflows/ci.yml](../.github/workflows/ci.yml): lint → test (Postgres
  service) → build → push to GHCR.
- [k8s/](../k8s): `kubectl kustomize k8s/overlays/dev` — show GPU scheduling,
  HPAs, probes, secrets template.

## Teardown
```bash
docker compose down            # add -v to also drop volumes (DB, photos, models)
```

## Troubleshooting
- **First classifier start is slow** → it's downloading models; `CLASSIFIER_STUB=1`
  skips that. Watch `docker compose logs -f classifier`.
- **Port already in use** → change the `*_HOST_PORT` values in `.env`.
- **Result stuck on pending** → check `docker compose logs worker classifier`.
