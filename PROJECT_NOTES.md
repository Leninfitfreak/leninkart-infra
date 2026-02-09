# Project Notes (LeninKart Infra)

This file tracks ongoing issues, actions taken, and resolution steps. Append to this file for each change until project completion.

## 2026-02-09
Issue: Product/Order APIs returning 503 from UI; DB creds mismatch after moving to Vault; Kafka client disconnects and TLS verify errors in sidecars.

Actions Taken (Repo Changes):
- Added Vault auth reviewer ServiceAccount + ClusterRoleBinding in `platform/vault/config/06-vault-auth-rbac.yaml`.
- Added note `docs/VAULT_SETUP_NOTE.md` describing Vault setup and ExternalSecrets integration.
- Removed hardcoded Postgres secret manifest `platform/postgres/postgres-secret.yaml`.
- Added ExternalSecret for Postgres admin creds: `platform/external-secrets/applications/postgres-admin-secret.yaml`.
- Fixed invalid YAML in `platform/external-secrets/applications/product-service-db-secret.yaml`.
- Updated product/order deployments to load Vault secrets via `envFrom` when enabled:
  - `applications/product-service/helm/templates/deployment.yaml`
  - `applications/order-service/helm/templates/deployment.yaml`
- Removed hardcoded DB username/password from dev values and set DB secret names:
  - `applications/product-service/helm/values-dev.yaml`
  - `applications/order-service/helm/values-dev.yaml`
- Updated Kafka bootstrap server to service DNS (not pod DNS):
  - `applications/product-service/helm/values-dev.yaml`
  - `applications/order-service/helm/values-dev.yaml`
- Added Istio DestinationRules to enforce `ISTIO_MUTUAL` for services (ingress → service):
  - `platform/istio/config/destinationrules.yaml`
- Switched Postgres StatefulSet to a new identity to force fresh init (declarative reset):
  - `platform/postgres/postgres-statefulset.yaml` now uses `postgres-v2` + new PVC.

Actions Taken (Cluster/Runtime):
- Unsealed Vault and configured Kubernetes auth.
- Wrote Vault policy `leninkart-policy` and role `leninkart-role`.
- Added Vault secrets for DB creds:
  - `secret/leninkart/product-service/database`
  - `secret/leninkart/order-service/database`
  - `secret/leninkart/postgres/admin`
- Applied ExternalSecrets in `platform/external-secrets/applications`.

Current Status:
- Postgres is now running as `postgres-v2-0` with new PVC and Vault-backed credentials.
- Product/Order pods are running; endpoints exist.
- UI still shows intermittent 503 due to mTLS/Kafka issues before sync.

Next Steps:
- Commit and push the latest GitOps changes.
- Sync Argo apps: `istio-config-dev`, `dev-product-service`, `dev-order-service`, `postgres-dev`.
- Restart product/order deployments after sync to pick up new config.
- Verify:
  - `kubectl -n dev get endpoints leninkart-product-service`
  - `kubectl -n dev get endpoints leninkart-order-service`
  - UI `/api/products` and `/api/orders` return 200.

## 2026-02-09 (Follow-up)
Issue: Browser showing `TLS_error: CERTIFICATE_VERIFY_FAILED` and 503s from gateway to `/`, `/api/products`, `/api/orders`.

Actions Taken (Repo Changes):
- Updated Istio DestinationRules to **disable TLS** for dev services to stop gateway → service TLS verification failures:
  - `platform/istio/config/destinationrules.yaml`

Next Steps:
- Commit + push this change.
- Sync Argo app `istio-config-dev`.
- Restart `product-service` and `dev-order-service-order-service` deployments after sync.

## 2026-02-09 (Follow-up 2)
Issue: TLS verify failures persist on Kafka traffic and 503s still seen from gateway.

Actions Taken (Repo Changes):
- Added namespace-level PeerAuthentication in `dev` to allow plaintext (PERMISSIVE):
  - `platform/istio/config/peerauthentication-dev.yaml`

Next Steps:
- Commit + push.
- Sync Argo app `istio-config-dev`.
- Restart `product-service` and `dev-order-service-order-service` deployments.
