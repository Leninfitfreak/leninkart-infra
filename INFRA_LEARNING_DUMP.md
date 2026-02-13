# LeninKart Infra Learning Dump

This note is a learning guide for your current `leninkart-infra` repo.
It explains how the repo is organized, how deployment flows, and what each file does.

## 1) Mental model of this repo

- `argocd/` is the GitOps control plane definitions.
- `platform/` is shared cluster infrastructure (Kafka, Postgres, Istio, Vault, External Secrets, namespaces).
- `applications/` is Helm for business apps (frontend, order-service, product-service, ingress values).
- `observability/` is monitoring/tracing stack (Prometheus, Grafana, OTel, Jaeger).
- `docs/` and root markdown files are operational notes/reports.

## 2) Deployment flow (how changes become running pods)

1. You push to `dev` branch.
2. Argo CD root app (`argocd/leninkart-root.yaml`) watches `argocd/applications/dev`.
3. Child Argo Applications point to `platform/*`, `applications/*`, `observability/*` paths.
4. Argo sync applies YAML/Helm manifests to the `dev` namespace (and related namespaces).
5. Kubernetes reconciles Deployments/StatefulSets/Services.

## 3) Runtime architecture in your cluster

- Frontend calls backend APIs through Istio gateway/virtualservice.
- `product-service` writes product events and reads/writes Postgres.
- `order-service` consumes Kafka topic(s) and reads/writes Postgres.
- Vault stores secrets.
- External Secrets Operator syncs Vault secrets into K8s Secrets.
- Prometheus scrapes metrics, Grafana visualizes, Jaeger/OTel handle tracing.

## 4) File-by-file catalog

### Root files

- `README.md`: Main project overview, architecture, quick start commands.
- `PROJECT_NOTES.md`: Ongoing operational change log.
- `REPORT.md`: Infra/report artifact.
- `REFACTOR_REPORT_20260207_020219.md`: Refactor summary report.
- `CLEANUP_REPORT_20260204_073025.md`: Cleanup analysis report.
- `leninkart-write.hcl`: Vault policy/HCL reference.
- `helm_order-service_values-dev.yaml`: Standalone values snapshot (legacy/support file).
- `helm_product-service_values-dev.yaml`: Standalone values snapshot (legacy/support file).
- `remove.py`: Local helper script (non-declarative, not part of GitOps deployment).
- `voult.py`: Local helper/experimental script (name typo, non-declarative).
- `infraleninkart-infra`: Local artifact file (verify if needed; likely accidental).

### Argo CD core

- `argocd/leninkart-root.yaml`: Root app-of-apps. Entry point Argo watches.
- `argocd/project.yaml`: Argo AppProject with allowed repos/destinations/resources.

### Argo CD apps (dev)

- `argocd/applications/dev/frontend.yaml`: Argo app for frontend Helm chart.
- `argocd/applications/dev/product-service.yaml`: Argo app for product-service Helm chart.
- `argocd/applications/dev/order-service.yaml`: Argo app for order-service Helm chart.
- `argocd/applications/dev/kafka.yaml`: Argo app for Kafka manifests.
- `argocd/applications/dev/postgres.yaml`: Argo app for Postgres manifests.
- `argocd/applications/dev/istio-config.yaml`: Argo app for Istio config (gateway/virtualservice/etc).
- `argocd/applications/dev/vault.yaml`: Argo app for Vault core deployment.
- `argocd/applications/dev/vault-secretstore.yaml`: Argo app for SecretStore setup.
- `argocd/applications/dev/vault-secretstores.yaml`: Additional SecretStore/secretstore set.
- `argocd/applications/dev/vault-externalsecrets.yaml`: Argo app for ExternalSecret definitions.
- `argocd/applications/dev/external-secrets-operator.yaml`: Argo app for ESO installation/config.
- `argocd/applications/dev/prometheus.yaml`: Argo app for Prometheus.
- `argocd/applications/dev/grafana.yaml`: Argo app for Grafana.
- `argocd/applications/dev/jaeger.yaml`: Argo app for Jaeger.
- `argocd/applications/dev/otel-collector.yaml`: Argo app for OTel collector.

### Argo CD apps (staging/prod)

- `argocd/applications/staging/frontend.yaml`: Staging frontend app mapping.
- `argocd/applications/staging/product-service.yaml`: Staging product-service mapping.
- `argocd/applications/staging/order-service.yaml`: Staging order-service mapping.
- `argocd/applications/prod/frontend.yaml`: Prod frontend app mapping.
- `argocd/applications/prod/product-service.yaml`: Prod product-service mapping.
- `argocd/applications/prod/order-service.yaml`: Prod order-service mapping.

### Applications (Helm)

- `applications/README.md`: High-level application folder guide.

Frontend:
- `applications/frontend/helm/Chart.yaml`: Helm chart metadata.
- `applications/frontend/helm/values.yaml`: Base/default values.
- `applications/frontend/helm/values-dev.yaml`: Dev environment overrides.
- `applications/frontend/helm/templates/deployment.yaml`: Frontend Deployment template.
- `applications/frontend/helm/templates/service.yaml`: Frontend Service template.
- `applications/frontend/helm/templates/_helpers.tpl`: Template helpers/naming macros.

Order service:
- `applications/order-service/helm/Chart.yaml`: Helm chart metadata.
- `applications/order-service/helm/values-dev.yaml`: Dev overrides (image/env/bootstrap etc).
- `applications/order-service/helm/templates/deployment.yaml`: Order Deployment template.
- `applications/order-service/helm/templates/service.yaml`: Order Service template.
- `applications/order-service/helm/templates/_helpers.tpl`: Template helper macros.

Product service:
- `applications/product-service/helm/Chart.yaml`: Helm chart metadata.
- `applications/product-service/helm/values-dev.yaml`: Dev overrides for product-service.
- `applications/product-service/helm/templates/deployment.yaml`: Product Deployment template.
- `applications/product-service/helm/templates/service.yaml`: Product Service template.

Ingress:
- `applications/ingress/helm/Chart.yaml`: Ingress chart metadata/placeholder.
- `applications/ingress/helm/values-dev.yaml`: Dev values for ingress-related routing.

### Platform (shared infra)

- `platform/README.md`: Shared infra module summary.

Namespaces:
- `platform/namespaces/dev.yaml`: `dev` namespace definition.
- `platform/namespaces/staging.yaml`: `staging` namespace definition.
- `platform/namespaces/prod.yaml`: `prod` namespace definition.

Kafka:
- `platform/kafka/kafka.yaml`: Kafka StatefulSet in KRaft mode (2 brokers, storage, env).
- `platform/kafka/kafka-service.yaml`: Headless/service exposure for Kafka brokers.

Postgres:
- `platform/postgres/postgres-statefulset.yaml`: Postgres StatefulSet and DB pod config.
- `platform/postgres/postgres-service.yaml`: Postgres Service for in-cluster access.

Istio:
- `platform/istio/config/gateway.yaml`: Ingress gateway host/port entry.
- `platform/istio/config/virtualservice.yaml`: Path-based routing to frontend/product/order.
- `platform/istio/config/destinationrules.yaml`: Traffic policy/tuning for services.
- `platform/istio/config/peerauthentication-dev.yaml`: mTLS/auth mode for dev namespace.
- `platform/istio/config/telemetry.yaml`: Istio telemetry config.

Vault:
- `platform/vault/config/00-namespace.yaml`: Vault namespace.
- `platform/vault/config/01-serviceaccount.yaml`: Vault service account.
- `platform/vault/config/02-configmap.yaml`: Vault server config.
- `platform/vault/config/03-statefulset.yaml`: Vault StatefulSet/workload.
- `platform/vault/config/04-service.yaml`: Vault service (API/UI exposure in-cluster).
- `platform/vault/config/06-vault-auth-rbac.yaml`: RBAC for Vault Kubernetes auth token review.
- `platform/vault/config/policies/leninkart-policy.hcl`: Vault policy for app secret paths.

External Secrets:
- `platform/external-secrets/external-secrets-values.yaml`: ESO values/config input.
- `platform/external-secrets/secretstore.yaml`: SecretStore/ClusterSecretStore definition for Vault.
- `platform/external-secrets/applications/product-service-db-secret.yaml`: ExternalSecret for product DB creds.
- `platform/external-secrets/applications/order-service-db-secret.yaml`: ExternalSecret for order DB creds.
- `platform/external-secrets/applications/postgres-admin-secret.yaml`: ExternalSecret for postgres admin creds.
- `platform/external-secrets/applications/kafka-credentials.yaml`: ExternalSecret for Kafka-related creds.
- `platform/external-secrets/applications/app-config-secrets.yaml`: ExternalSecret for app-level config/secrets.

### Observability

- `observability/README.md`: Monitoring/tracing stack summary.

Prometheus:
- `observability/prometheus/prometheus.yaml`: Aggregated/top-level Prometheus manifest.
- `observability/prometheus/prometheus-configmap.yaml`: Scrape config/jobs.
- `observability/prometheus/prometheus-rbac.yaml`: Prometheus RBAC rules.
- `observability/prometheus/prometheus-deployment.yaml`: Prometheus deployment/service wiring.

Grafana:
- `observability/grafana/grafana.yaml`: Aggregated/top-level Grafana manifest.
- `observability/grafana/grafana-deployment.yaml`: Grafana deployment/service config.
- `observability/grafana/grafana-datasources.yaml`: Datasource provisioning (Prometheus/Jaeger).

Jaeger:
- `observability/jaeger/jaeger.yaml`: Jaeger deployment/service.
- `observability/jaeger/jaeger-all-in-one.yaml`: Alternate all-in-one Jaeger manifest.

OpenTelemetry:
- `observability/otel/collector-configmap.yaml`: OTel pipeline receivers/processors/exporters.
- `observability/otel/collector-deployment.yaml`: OTel collector deployment.
- `observability/otel/collector-service.yaml`: OTel service endpoints.
- `observability/otel/01-configmap.yaml`: Additional OTel config variant.
- `observability/otel/02-deployment.yaml`: Additional OTel deployment variant.

### Docs and scripts

Docs:
- `docs/VAULT_SETUP.md`: Main Vault setup guide.
- `docs/VAULT_SETUP_NOTE.md`: Project-specific Vault integration notes.
- `docs/VAULT_ARGOCD_INIT.md`: Vault + Argo initialization steps.
- `docs/REPO_NETWORK_AND_RECOMMENDATIONS.md`: Networking review and recommendations.

Scripts:
- `scripts/vault-commands.ps1`: PowerShell helper commands for Vault operations.
- `scripts/vault-quickstart.sh`: Bash helper quickstart for Vault commands.

## 5) Current important coupling points

- Kafka broker DNS expected by apps must match `kafka-0.kafka.dev.svc.cluster.local:9092` and `kafka-1.kafka.dev.svc.cluster.local:9092`.
- Istio virtual service paths must match frontend API routes (`/api/products`, `/api/orders`, auth paths if used).
- ExternalSecret target secret names must match env variable references in Helm deployment templates.
- If Vault path keys change, ExternalSecret mappings must be updated or apps fail at startup.

## 6) What to learn first (recommended order)

1. `argocd/leninkart-root.yaml` and `argocd/applications/dev/*.yaml`.
2. `applications/*/helm/templates/deployment.yaml` + `values-dev.yaml`.
3. `platform/istio/config/virtualservice.yaml` and `gateway.yaml`.
4. `platform/external-secrets/*` + `platform/vault/config/*`.
5. `platform/kafka/*` and `platform/postgres/*`.
6. `observability/*` for metrics and traces.

## 7) Cleanup candidates (non-GitOps/legacy)

Review and remove if no longer needed:
- `voult.py`
- `remove.py`
- `infraleninkart-infra`
- `helm_order-service_values-dev.yaml`
- `helm_product-service_values-dev.yaml`
- duplicate OTel/Jaeger manifest variants if only one path is active

## 8) Quick commands you will use daily

- Argo root sync check:
  - `kubectl -n argocd get applications`
- Dev pod health:
  - `kubectl -n dev get pods`
- Kafka health:
  - `kubectl -n dev get pods -l app=kafka`
- Order logs:
  - `kubectl -n dev logs deploy/dev-order-service-order-service --tail=200`
- Product logs:
  - `kubectl -n dev logs deploy/product-service --tail=200`
- Frontend access:
  - `kubectl -n dev port-forward svc/leninkart-frontend 8080:80`

---
Generated for learning from current repo snapshot.
