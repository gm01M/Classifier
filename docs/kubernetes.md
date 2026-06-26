# Kubernetes Strategy — scaling, secrets, observability

Manifests live in [`k8s/`](../k8s) as a kustomize **base** plus **dev/prod**
overlays. They are provided and validated (`kubectl kustomize k8s/overlays/dev`)
but, per the brief, the live-cluster apply is documented rather than run against a
real cluster.

```
k8s/
  base/        namespace, config, secret template, postgres, redis, minio,
               migrate-job, webapp(+worker), classifier(GPU), ingress, hpa
  overlays/
    dev/       1 replica each, :dev image tag
    prod/      3 web replicas, :1.0.0 image tag, managed-DB guidance
```

Apply (after supplying the real Secret):
```bash
kubectl apply -f k8s/base/secret.example.yaml   # <- replace with a real Secret first!
kubectl apply -f k8s/base/migrate-job.yaml       # pre-deploy migrations
kubectl apply -k k8s/overlays/prod
```

## Scaling

| Tier | How it scales |
|---|---|
| **webapp** | `HorizontalPodAutoscaler` on CPU (2→8). Stateless; scales with RPS. |
| **worker** | HPA on CPU (2→10) as a proxy for queue depth. Production: a **KEDA** ScaledObject on Celery/Redis queue length is the precise signal. |
| **classifier** | GPU-pinned (`nvidia.com/gpu: 1`, `nodeSelector` + toleration). Modest HPA (1→3); real elasticity comes from the **GPU node-pool cluster-autoscaler**. GPUs are scarce/expensive, so we scale conservatively and keep inference async so bursts queue rather than drop. |
| **postgres** | Managed (RDS/Cloud SQL) in real cloud; front with **PgBouncer** for connection pooling under autoscaling. StatefulSet only for self-host demo. |
| **redis / minio** | Managed (ElastiCache / S3) in cloud; StatefulSet/Deployment for self-host. |

The async, message-driven design is what makes scaling safe: the web tier never
blocks on the GPU, so a traffic spike grows the Redis queue (absorbed by worker
+ GPU autoscaling) instead of failing user requests.

## Secrets

- Application config → `ConfigMap` (`webapp-config`, `classifier-config`).
- Sensitive values → `Secret` named `platform-secrets`, consumed via `secretRef`/
  `secretKeyRef`. **The repo ships only a template** (`secret.example.yaml`);
  the real Secret is supplied out-of-band.
- Recommended production patterns (documented in the template):
  - **Sealed Secrets** — commit an encrypted `SealedSecret` to git (GitOps-safe).
  - **External Secrets Operator** — sync from AWS Secrets Manager / Vault / GCP SM.
  - Or `kubectl create secret …` from the CI/CD pipeline.
- `.env`/secrets are never baked into images; containers read them at runtime.

## Observability

- **Metrics:** `webapp` exposes `/metrics` (django-prometheus); `classifier`
  exposes `/metrics` (prometheus-fastapi-instrumentator). Pods carry
  `prometheus.io/scrape` annotations for a Prometheus scrape config; visualise in
  **Grafana** (latency, error rate, queue depth, GPU utilisation via DCGM).
- **Logs:** structured **JSON logging** to stdout (python-json-logger / uvicorn),
  ready for Loki/ELK/CloudWatch aggregation.
- **Health:** liveness (`/healthz`) and readiness (`/readyz`, DB/model checks)
  probes on every workload; the classifier uses a generous **startupProbe**
  because the first start downloads models onto the GPU.
- **Tracing (next step):** OpenTelemetry instrumentation across webapp → Celery →
  classifier for end-to-end submission traces.
- **Errors (next step):** Sentry SDK in both services.

## Rollouts & resilience

- Migrations run in a **pre-deploy Job**, so web replicas never race.
- Rolling updates gated by readiness probes; `kubectl rollout status` in the CD
  workflow.
- Resource `requests`/`limits` set on every container for bin-packing and QoS.
- All app containers run **non-root** (`runAsNonRoot`, UID 10001).
