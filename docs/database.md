# Database Design

## Choice: PostgreSQL — and why

| Requirement | Why Postgres fits |
|---|---|
| Relational integrity (users ↔ submissions) | Foreign keys, transactions, ACID. |
| Admin filtering by age range, gender, location, country | Rich B-tree + composite indexing; efficient range + equality predicates. |
| Flexible classification output | Native `JSONB` column (+ optional GIN index). |
| Free-text search on name/description | `ILIKE` now; can graduate to `tsvector`/GIN full-text. |
| Operational maturity | First-class Django support, widely managed (RDS/Cloud SQL). |

Photos are **not** stored in the database — only the object-storage key. This
keeps rows small and lets the DB and blob store scale independently.

## Schema

### `accounts_user`
Custom user; **email is the login identifier** (no username). `is_staff` is the
admin-role flag (RBAC). Passwords hashed with Argon2 (PBKDF2 fallback).

Also holds the **onboarding profile** collected at registration: `full_name`,
`age`, `place_of_living`, `gender`, `country_of_origin`, `description` (nullable
so superusers can exist without a full profile). Each photo submission snapshots
these onto the submission row, so the submission table remains the unit of admin
filtering and historical records don't change when a user later edits their
profile.

### `submissions_submission`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Non-enumerable identifier. |
| `owner_id` | FK → user | `CASCADE` on delete. |
| `name` | varchar(150) | |
| `age` | smallint | validated `0..120`. |
| `place_of_living` | varchar(120) | "location" filter. |
| `gender` | varchar(12) | enum: male/female/other/undisclosed. |
| `country_of_origin` | varchar(80) | |
| `description` | text(≤2000) | optional. |
| `photo_key` | varchar(255) | object-storage reference. |
| `photo_content_type` | varchar(40) | normalised to `image/jpeg`. |
| `status` | varchar(12) | pending/done/failed/rejected. |
| `classification_result` | JSONB | nullable. |
| `error_detail` | varchar(255) | reason for failed/rejected. |
| `created_at` / `updated_at` | timestamptz | |

## Indexing strategy

Tuned for the admin filters and the worker's status scans:

| Index | Columns | Serves |
|---|---|---|
| `sub_age_idx` | `age` | age range filters |
| `sub_gender_idx` | `gender` | gender filter |
| `sub_country_idx` | `country_of_origin` | country filter |
| `sub_place_idx` | `place_of_living` | location filter |
| `sub_created_idx` | `created_at` | ordering / date filters |
| `sub_status_idx` | `status` | worker + status filter |
| `sub_gender_country_age_idx` | `(gender, country_of_origin, age)` | the common combined admin query |

The composite index covers the frequent "gender + country + age-range" filter in
one index scan. A GIN index on `description` (full-text) or on
`classification_result` (JSONB) can be added if those become query dimensions.

## Migrations

Django migrations are the source of truth (`accounts/migrations`,
`submissions/migrations`), generated with `makemigrations` and applied with
`migrate`.

- **Local/compose**: the webapp entrypoint runs `migrate` on startup.
- **Kubernetes**: a one-shot pre-deploy **Job** (`k8s/base/migrate-job.yaml`)
  runs `migrate` + `init_storage` + `ensure_admin`, so web pods never race on
  migrations.

## Configuration notes

- `CONN_MAX_AGE=60` for persistent connections; front Postgres with **PgBouncer**
  in production to bound connection count under autoscaling.
- Metrics-wrapped DB backend (`django_prometheus...postgresql`) exposes query
  metrics at `/metrics`.
- Managed-DB swap is a one-line change: point `POSTGRES_HOST`/credentials at the
  managed endpoint and drop the in-cluster `postgres.yaml`.
