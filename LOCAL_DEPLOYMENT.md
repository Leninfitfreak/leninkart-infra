# LeninKart Local Deployment (k3d + Docker Compose)

## What this stack does

This workspace runs:
- Kafka in Docker Compose (`kafka-platform`).
- Observer stack in Docker Compose (`observer-stack/deploy/docker`).
- Application platform in a dedicated k3d cluster (`leninkart-dev`), deployed via GitOps (ArgoCD).

## Branch model used by deployment tasks

- `leninkart-infra` → `dev` branch for platform and manifests.
- `leninkart-product-service` → `dev`.
- `leninkart-order-service` → `dev`.
- `leninkart-frontend` → `dev`.
- `kafka-platform` and `observer-stack` → `main`.

## Start local environment

From this repo:

```powershell
.\scripts\up-local.ps1
```

## Stop local environment

```powershell
.\scripts\down-local.ps1
```

Keep cluster and only remove app/docker workloads:

```powershell
.\scripts\down-local.ps1 -KeepCluster
```

## Verify local environment

```powershell
.\scripts\verify-local.ps1
```

Run full validation engine (if dependencies are available):

```powershell
.\scripts\verify-local.ps1 -RunValidationEngine
```

## Endpoints

- Frontend: `http://127.0.0.1/`
- Observer Stack: `http://127.0.0.1:8080`
- Deep Observer: `http://127.0.0.1:3000`
- Deep Observer API health: `http://127.0.0.1:8081/health`
- ArgoCD UI: port-forward `kubectl port-forward -n argocd svc/argocd-server 8085:443`

## Validation artifacts

- Runtime checks: `LOCAL_DEPLOYMENT.md`
- Latest run output: `local-deployment-report.json`

