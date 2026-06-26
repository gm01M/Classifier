# Architecture

## Goal & shape

A web platform with two responsibilities — a **user journey** (register/login →
submit photo + metadata → get a classification result) and an **admin panel**
(filter/search/retrieve submissions) — decomposed into microservices,
containerized, and cloud-deployable.

The decomposition keeps a clear seam between the **stateless web/business tier**
and the **GPU model tier**, which have very different scaling and dependency
profiles.

## Components

| Component | Stack | Responsibility | State |
|---|---|---|---|
| **webapp** | Django, DRF, HTMX, Gunicorn | HTMX UI (user + admin), REST API + Swagger, auth + RBAC, validation, submissions, orchestration | stateless |
| **worker** | Celery (same image) | Consume classification jobs, call the classifier, persist results | stateless |
| **classifier** | FastAPI, PyTorch/transformers | GPU model inference (`/v1/classify`) + NSFW gate | stateless (model in memory) |
| **postgres** | PostgreSQL 16 | Users + submission metadata | stateful |
| **redis** | Redis 7 | Celery broker/result backend + throttle cache | stateful (ephemeral) |
| **minio** | MinIO (S3 API) | Photo objects (private bucket) | stateful |

The two **microservices proper** are `webapp` and `classifier` (the `worker`
shares the webapp image/codebase but is a separately scaled deployment). This
satisfies the "≥2 microservices" requirement with a meaningful boundary rather
than an artificial split.

## Request flow (submission → result)

0. **Onboarding** — At registration the user provides their profile (name, age,
   place of living, gender, country of origin, optional description), stored on
   the user account and editable later on the profile page.
1. **Upload** — User submits a **photo only** (HTMX form or `POST /api/submissions`);
   the current profile metadata is **snapshotted** onto the submission record, so
   admin filtering stays per-submission and historical records are immutable.
2. **Validate & sanitise** — `webapp` runs the image safety pipeline: size check,
   magic-byte sniff against an allowlist, `Pillow.verify()`, then re-encode to
   strip EXIF/GPS (see [docs/safety.md](docs/safety.md)).
3. **Store** — Photo bytes → MinIO (object key only is kept in the DB); metadata
   row written with `status=PENDING`.
4. **Enqueue** — A Celery task is published to Redis; the HTTP request returns
   immediately (201) so the user is never blocked on the GPU.
5. **Classify** — A `worker` pulls the job, downloads the photo from MinIO, and
   calls `classifier` `POST /v1/classify`.
6. **Persist** — Worker writes `classification_result` and flips status to
   `DONE` (or `REJECTED` on NSFW / `FAILED` after retries).
7. **Reveal** — The detail page polls `GET /submissions/{id}/result` via HTMX
   (`hx-trigger="every 2s"`) and swaps in the result card, dropping the poll once
   the status leaves `PENDING`.

This async, message-driven design is the core architectural decision: it isolates
unpredictable GPU latency, lets the GPU tier scale on its own, and gives a clean
HTMX polling UX.

## Why these choices

- **Django + HTMX for both UIs.** One framework covers auth, sessions, CSRF,
  ORM, migrations, the Django admin, and server-rendered templates. HTMX adds
  live filtering and result polling with no SPA toolchain. DRF + drf-spectacular
  layer a validated, documented JSON API over the same models.
- **Separate FastAPI GPU service.** Model serving has heavy, GPU-specific
  dependencies (torch/CUDA) and a different scaling unit (GPU memory, not RPS).
  Keeping it behind a narrow HTTP contract means the web image stays small, the
  model is swappable, and the GPU tier scales independently. FastAPI gives async
  I/O and auto-generated docs.
- **Celery + Redis.** The standard Django async stack; `acks_late` +
  `prefetch_multiplier=1` give fair dispatch and at-least-once semantics suited
  to slow tasks, with bounded retries.
- **PostgreSQL.** Strong typing + indexing for the admin filters and JSONB for
  the flexible classification result. See [docs/database.md](docs/database.md).
- **MinIO/S3.** Object storage is the right home for photos; the DB holds only a
  reference. Private bucket + short-lived presigned GET URLs keep photos
  non-enumerable.

## Communication & contracts

- **Browser ↔ webapp**: HTTPS; HTML/HTMX for pages, JSON for the API. JWT for API
  clients, session cookies for the browser UI.
- **webapp/worker ↔ classifier**: internal HTTP, `multipart` image →
  `ClassificationResult` JSON. `422` is the agreed "content blocked" signal that
  the worker maps to a `REJECTED` submission.
- **webapp/worker ↔ Redis**: Celery protocol.
- **webapp/worker ↔ MinIO**: S3 API (boto3).
- **everything ↔ Postgres**: SQL via the Django ORM.

## Security & RBAC (summary)

JWT (SimpleJWT) + Django sessions; Argon2 password hashing; `is_staff` gates all
admin endpoints; users only ever see their own submissions; secrets come from the
environment / K8s Secrets; HTTPS enforcement is env-toggled (on in cluster, off
for the local HTTP demo). Details in [docs/safety.md](docs/safety.md).

## Cloud / Kubernetes

Stateless tiers scale horizontally (HPAs); the classifier is pinned to a GPU node
pool and scales conservatively; data tiers are managed services in real cloud.
Strategy in [docs/kubernetes.md](docs/kubernetes.md).

## Trade-offs & possible extensions

- **Worker calls classifier over HTTP** (vs. embedding the model in the worker):
  one extra hop, but independent GPU scaling and a swappable model — worth it.
- **HTMX polling** (vs. WebSockets/SSE): simplest reliable option; SSE could
  reduce request volume later.
- **MinIO/Redis/Postgres as in-cluster StatefulSets** for the self-host demo;
  production should use managed equivalents (RDS/ElastiCache/S3).
- **Queue-depth autoscaling**: HPAs use CPU today; a KEDA ScaledObject on Celery
  queue length would be the production upgrade.
