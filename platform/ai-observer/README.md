# AI Observer (Infra Manifests)

This folder is infra-only (Kubernetes manifests for GitOps).

Application source is in a separate repository:
- `https://github.com/Leninfitfreak/ai-observer-agent`

## Structure

```text
platform/ai-observer/
  base/
    serviceaccount.yaml
    configmap-env.yaml
    deployment.yaml
    service.yaml
    kustomization.yaml
  overlays/dev/kustomization.yaml
  alertmanager-webhook-snippet.yaml
```

## Environment Variables

- `PROMETHEUS_URL` (default `http://prometheus:9090`)
- `LOKI_URL` (default `http://loki-gateway:80`)
- `JAEGER_URL` (default `http://jaeger-query:16686`)
- `LLM_PROVIDER` (default `ollama`)
- `LLM_MODEL` (default `gpt-oss:20b`)
- `OLLAMA_URL` (default `https://ollama.com`)
- `ALL_SERVICES` (default `product-service,order-service`) used when `service=all`
- `OPENAI_API_KEY` via `ai-observer-secrets` secret (used for cloud auth)
- `OPENAI_BASE_URL` kept for optional OpenAI-compatible provider mode
- `DEFAULT_NAMESPACE` (default `dev`)

Secret setup guide:
- `platform/ai-observer/base/secrets-template.md`

## API

- `GET /healthz`
- `POST /webhook/alertmanager`

Response shape:

```json
{
  "context": {
    "alert": {},
    "metrics": {},
    "logs_summary": "...",
    "trace_summary": "...",
    "datasource_errors": {}
  },
  "analysis": {
    "probable_root_cause": "...",
    "impact_level": "Low|Medium|High",
    "recommended_remediation": "...",
    "confidence_score": "85%"
  }
}
```

## Deploy In Minikube

1. Ensure app image is published by app repo workflow:
- `ghcr.io/leninfitfreak/ai-observer-agent:dev`

2. Apply manifests:

```powershell
kubectl apply -k platform/ai-observer/overlays/dev
```

3. Verify:

```powershell
kubectl -n dev get deploy,pod,svc | findstr /I "ai-observer"
kubectl -n dev logs deploy/ai-observer --tail=100
```

## Manual Webhook Test

```powershell
kubectl -n dev port-forward svc/ai-observer 8080:8080
```

```powershell
curl -X POST http://127.0.0.1:8080/webhook/alertmanager `
  -H "Content-Type: application/json" `
  -d '{
    "status":"firing",
    "receiver":"ai-observer-webhook",
    "alerts":[
      {
        "status":"firing",
        "labels":{
          "alertname":"High5xxRate",
          "namespace":"dev",
          "service":"order-service",
          "severity":"critical"
        },
        "annotations":{"summary":"Test alert from manual curl"}
      }
    ]
  }'
```

## Alertmanager Snippet

See `platform/ai-observer/alertmanager-webhook-snippet.yaml` and merge it into your Alertmanager config.
