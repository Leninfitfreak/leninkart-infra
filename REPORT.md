======================================================================
LeninKart GitOps Refactor (based on dump6.txt)
Mode: APPLY
======================================================================

[1] Removing junk scripts & artifacts
[REMOVED] C:\Projects\infra\leninkart-infra\fix.py

[2] Removing junk directories

[3] Removing NGINX ingress manifests

[4] Removing imperative Vault init artifacts
[REMOVED] C:\Projects\infra\leninkart-infra\platform\vault\config\05-init-job.yaml
[REMOVED] C:\Projects\infra\leninkart-infra\platform\vault\config\policies\setup-k8s-auth.sh

[5] Ensuring namespace manifests exist
[CREATED] C:\Projects\infra\leninkart-infra\platform\namespaces\dev.yaml
[CREATED] C:\Projects\infra\leninkart-infra\platform\namespaces\staging.yaml
[CREATED] C:\Projects\infra\leninkart-infra\platform\namespaces\prod.yaml

[6] Scanning for plaintext secrets (BLOCKING)
[❌ PLAINTEXT SECRET] C:\Projects\infra\leninkart-infra\helm_order-service_values-dev.yaml
[❌ PLAINTEXT SECRET] C:\Projects\infra\leninkart-infra\platform\external-secrets\applications\order-service-db-secret.yaml
[❌ PLAINTEXT SECRET] C:\Projects\infra\leninkart-infra\platform\external-secrets\applications\product-service-db-secret.yaml
[❌ PLAINTEXT SECRET] C:\Projects\infra\leninkart-infra\applications\product-service\helm\values-dev.yaml
[❌ PLAINTEXT SECRET] C:\Projects\infra\leninkart-infra\applications\order-service\helm\values-dev.yaml

[7] Normalizing line endings (LF)

[8] Writing REPORT.md