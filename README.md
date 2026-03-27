# LeninKart Infrastructure

GitOps source of truth for the LeninKart dev platform.

## What This Repo Owns

This repository defines the Kubernetes-side platform that ArgoCD reconciles for LeninKart.

Current live scope:

- application deployments
  - `frontend`
  - `product-service`
  - `order-service`
- ingress and routing
- PostgreSQL
- Vault and External Secrets integration
- observability apps
  - Grafana
  - Prometheus
  - Loki
  - Promtail
  - Tempo
- ArgoCD app-of-apps definitions for the dev environment

The active GitOps branch for the current local platform is `dev`.

## Current GitOps Model

- root application: `argocd/leninkart-root.yaml`
- target revision: `dev`
- application definitions: `argocd/applications/dev/`
- namespace focus: `dev`, with supporting namespaces such as `argocd`, `vault`, and `external-secrets-system`

ArgoCD currently reconciles the real app set under `argocd/applications/dev`, including:

- `frontend-dev`
- `dev-product-service`
- `dev-order-service`
- `postgres-dev`
- `grafana-dev`
- `prometheus-dev`
- `loki-dev`
- `promtail-dev`
- `tempo-dev`
- `vault`
- `vault-secretstore`
- `vault-externalsecrets`
- `dev-ingress`
- `loadtest-dev`
- `argocd-config`

## Repository Layout

```text
leninkart-infra/
  applications/
    frontend/
    product-service/
    order-service/
    ingress/
  argocd/
    leninkart-root.yaml
    applications/dev/
  observability/
    grafana/
    prometheus/
    loki/
    promtail/
    tempo/
  platform/
    ingress/
    loadtest/
    vault/
    argocd-config/
  scripts/
    up-local.ps1
    down-local.ps1
    reseed-vault-local.ps1
    verify-local.ps1
```

## Local Environment

This repo is currently aligned to the local LeninKart dev environment:

- cluster: `k3d-leninkart-dev`
- GitOps branch: `dev`
- primary workload namespace: `dev`

## How Changes Flow

1. Update the relevant app or platform manifest or Helm values in this repo.
2. Commit the change to `dev`.
3. ArgoCD reconciles the matching application.
4. Runtime status is verified in ArgoCD as `Synced` and `Healthy`.

For Jira-driven deployments, this repo is updated by the separate `deployment-poc` orchestrator.

## Key Docs

- [Vault Setup](docs/VAULT_SETUP.md)
- [Vault + ArgoCD Initialization](docs/VAULT_ARGOCD_INIT.md)
- [ArgoCD Repo-Server Recovery](ARGOCD_REPO_SERVER_RECOVERY.md)

## Notes

- This repo is intentionally declarative. Local helper scripts may assist cluster bootstrap or verification, but the deployed state is defined by Git-managed manifests and values.
- Deprecated local analysis dumps, report files, and one-off helper artifacts have been removed to keep the repo focused on the active GitOps system.
