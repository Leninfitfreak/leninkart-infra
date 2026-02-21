# AI Observer (Lightweight)

This is a reusable, lightweight observability agent for Kubernetes.

It runs in two modes:
- Detection (implemented): rule-based checks on Prometheus/Loki/Jaeger
- Assisted remediation (future): human-approved action suggestions

## Structure

- `base/`: reusable manifests + Python observer loop
- `overlays/dev/`: environment-specific settings (URLs, jobs, namespace)

## What it does

- Checks service availability (`up`) for monitored jobs
- Computes 5xx error ratio from HTTP metrics
- Computes p95 latency from histogram metrics
- Counts recent error logs from Loki
- Checks Jaeger API reachability
- Prints structured JSON summaries to container logs

## Reuse in another project

1. Copy `platform/ai-observer/`.
2. Create a new overlay (for example `overlays/staging`).
3. Patch env vars in overlay to your stack URLs and jobs.
4. Add one Argo CD `Application` pointing to that overlay path.

