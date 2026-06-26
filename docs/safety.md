# Safety Rules — what, where, why

The brief asks us to add safety rules and explain what/where/why. We implement
**defence in depth** across the upload boundary, the classification boundary, the
auth boundary, and storage. Each rule below lists the **what**, the **where**
(file), and the **why**.

## 1. Upload content validation (not extension trust)
- **What:** Reject anything that isn't a real JPEG/PNG/WebP within the size limit.
  We sniff **magic bytes** and run `Pillow.verify()` rather than trusting the
  client's filename or `Content-Type`.
- **Where:** [`webapp/common/image_safety.py`](../webapp/common/image_safety.py)
  (`validate_and_sanitize`), enforced in the DRF serializer and the HTMX form
  ([`submissions/serializers.py`](../webapp/submissions/serializers.py),
  [`submissions/forms.py`](../webapp/submissions/forms.py)). Size is also capped
  by `DATA_UPLOAD_MAX_MEMORY_SIZE` and the ingress `proxy-body-size`.
- **Why:** Block malformed files, oversized payloads (DoS), decompression bombs,
  and content-type spoofing.

## 2. EXIF/GPS stripping + re-encode
- **What:** Every accepted image is decoded and **re-encoded to clean JPEG**,
  dropping all EXIF/metadata (including GPS) and any trailing/embedded data.
- **Where:** `image_safety.validate_and_sanitize` (the `Image.save(..., "JPEG")`
  step).
- **Why:** Privacy (location/PII often hides in EXIF) and neutralising payloads
  smuggled in metadata.

## 3. NSFW / content-safety gate
- **What:** Before a result is stored, the image is scored by an NSFW classifier;
  if it exceeds `NSFW_THRESHOLD` the submission is **rejected** (status
  `rejected`), not classified.
- **Where:** [`classifier/app/model.py`](../classifier/app/model.py)
  (`_nsfw_score`, `SafetyBlocked`) → returns HTTP `422`; the worker maps that to
  `REJECTED` in [`submissions/tasks.py`](../webapp/submissions/tasks.py).
- **Why:** An open photo-upload surface invites abuse; screen it before it's
  surfaced to admins or persisted as a result.

## 4. Rate limiting / throttling
- **What:** Per-user/per-IP throttles — `auth` (10/min) on register/login,
  `upload` (20/min) on submission create, plus global anon/user defaults.
- **Where:** DRF throttle config in
  [`config/settings/base.py`](../webapp/config/settings/base.py) and
  `throttle_scope`s in
  [`accounts/api_views.py`](../webapp/accounts/api_views.py) /
  [`submissions/api_views.py`](../webapp/submissions/api_views.py). Backed by Redis.
- **Why:** Mitigate brute-force credential attacks and upload spam/DoS.

## 5. AuthN + RBAC on every boundary
- **What:** All endpoints require authentication; **admin** endpoints/pages
  require `is_staff`; users can only access **their own** submissions.
- **Where:** [`common/permissions.py`](../webapp/common/permissions.py)
  (`IsAdminUserRole`, `IsOwnerOrAdmin`), per-view `permission_classes`, queryset
  scoping in [`submissions/api_views.py`](../webapp/submissions/api_views.py), and
  `user_passes_test(is_staff)` on the HTMX admin views
  ([`submissions/admin_views.py`](../webapp/submissions/admin_views.py)).
- **Why:** Enforce least privilege; prevent horizontal/vertical privilege
  escalation.

## 6. Input validation & output escaping
- **What:** Strongly-typed validation (age bounds, gender/country, length caps)
  on every field; template auto-escaping for all rendered user content.
- **Where:** DRF serializers + Django forms + model validators
  ([`submissions/models.py`](../webapp/submissions/models.py)); Django templates
  escape by default.
- **Why:** Data integrity and XSS prevention.

## 7. Private storage + presigned URLs
- **What:** Photos live in a **private** bucket; the UI/API hand out short-lived
  (default 15 min) presigned GET URLs instead of public links.
- **Where:** [`webapp/common/storage.py`](../webapp/common/storage.py)
  (`presigned_get_url`), keys namespaced per user
  (`submissions/{user_id}/{uuid}.jpg`).
- **Why:** Photos aren't publicly enumerable; access is time-bounded.

## Supporting hardening (not numbered, but applied)
- **Argon2** password hashing; **JWT + sessions**; **CSRF** on all HTMX forms.
- **HTTPS enforcement** (SSL redirect, secure cookies, HSTS) — env-toggled, on in
  Kubernetes (TLS at ingress), relaxed only for the local plain-HTTP demo
  ([`config/settings/prod.py`](../webapp/config/settings/prod.py)).
- **Non-root containers** (UID 10001) and minimal base images.
- **Secrets via env / K8s Secrets** — never committed (`.env` is gitignored;
  only `.env.example` and a Secret *template* are in the repo).
- **UUID primary keys** for submissions (non-sequential, non-guessable).

## Where you'd extend next
Face-presence check (reject person-less photos), virus scanning (ClamAV) on
upload, audit logging of admin access, and signed-URL IP pinning.
