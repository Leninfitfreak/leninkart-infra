# Multi-Cluster Observability (Additive)

This module adds multi-cluster telemetry ingestion and storage without modifying existing single-cluster AI observer endpoints.

## Components

- `observer-agent/`: lightweight Python cluster-side shipper (`observer-agent:latest`)
- `central-collector/`: FastAPI service with `/api/agent/push`
- `k8s/`: Kubernetes manifests for Minikube/dev
- `frontend-addon/`: drop-in UI cluster filter helpers
- `scripts/`: telemetry generator and curl validation scripts

## Backward Compatibility

- Existing AI observer endpoints remain unchanged (`/healthz`, `/webhook/alertmanager`).
- New APIs are additive:
  - `POST /api/agent/push`
  - `GET /api/observability/history?cluster=<id>`
  - `GET /api/observability/dashboard?cluster=<id>`
- `cluster` query parameter is optional. If omitted, current behavior remains default/unfiltered.

## Build Images

```powershell
docker build -t observer-agent:latest platform/ai-observer/multicluster/observer-agent
docker build -t ai-observer-central-collector:latest platform/ai-observer/multicluster/central-collector
```

## Deploy to Minikube

```powershell
kubectl apply -k platform/ai-observer/multicluster
kubectl -n dev get deploy,svc | findstr /I "observer-agent ai-observer-central-collector ai-observer-central-otel"
```

## Test push endpoint

```powershell
kubectl -n dev port-forward svc/ai-observer-central-collector 8081:8081
python platform/ai-observer/multicluster/scripts/generate_telemetry.py --url http://127.0.0.1:8081/api/agent/push --cluster minikube-dev --count 3
```

## Local central storage stack

```powershell
cd observability/multicluster-stack
docker compose up -d --build
```

Grafana: `http://127.0.0.1:3000`