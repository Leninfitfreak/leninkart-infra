# Observer Agent (Infra)

This repo contains only the lightweight cluster-side `observer-agent` deployment.
No central AI backend deployment manifests are included here.

## Required Environment Variables

- `CLUSTER_ID`
- `CENTRAL_URL`
- `AGENT_TOKEN`
- `PROM_URL`
- `PUSH_INTERVAL`
- `ENVIRONMENT`

## Files

- `base/configmap.yaml`: non-sensitive environment values
- `base/secret-template.yaml`: `AGENT_TOKEN`
- `base/deployment.yaml`: agent deployment with env-based config

## Deploy (Dev Overlay)

```powershell
kubectl apply -k platform/observer-agent/overlays/dev
```

## Onboard New Cluster

Only set these values and deploy:

1. `CLUSTER_ID=<new-cluster>`
2. `CENTRAL_URL=https://<central-host>/api/agent/push`
3. `AGENT_TOKEN=<shared-secret>`

No code changes are required.