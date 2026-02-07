# Vault Setup Note (LeninKart)

This note summarizes what was configured and how Vault integrates with External Secrets in this repo.

## What was configured
- Vault was unsealed and root login was used once to complete setup.
- Kubernetes auth was configured so Vault can validate ServiceAccount JWTs.
- Vault policy `leninkart-policy` was uploaded.
- Kubernetes auth role `leninkart-role` was created, bound to ServiceAccount `vault-auth` in namespace `dev`.
- Database secrets were written to:
  - `secret/leninkart/product-service/database`
  - `secret/leninkart/order-service/database`

## GitOps manifests added
- `platform/vault/config/06-vault-auth-rbac.yaml`
  - Creates ServiceAccount `vault-auth` in namespace `vault`
  - Binds `system:auth-delegator` so Vault can review JWTs

## External Secrets integration (expected)
ExternalSecrets are configured to read from Vault using:
- ClusterSecretStore: `platform/external-secrets/secretstore.yaml`
- ServiceAccount ref: `vault-auth`
- Vault role: `leninkart-role`

ExternalSecret resources expect these paths to exist in Vault:
- `secret/leninkart/product-service/config`
- `secret/leninkart/order-service/config`
- `secret/leninkart/product-service/database`
- `secret/leninkart/order-service/database`
- `secret/leninkart/kafka/credentials`

Only the database paths were populated in this session.

## Commands used (for repeatability)
Unseal + login:
```bash
vault operator unseal <UNSEAL_KEY>
vault login <ROOT_TOKEN>
```

Configure Kubernetes auth:
```bash
vault write auth/kubernetes/config \
  token_reviewer_jwt="<JWT>" \
  kubernetes_host="https://kubernetes.default.svc:443" \
  kubernetes_ca_cert="<CA_PEM>"
```

Policy + role:
```bash
vault policy write leninkart-policy /vault/policies/leninkart-policy.hcl

vault write auth/kubernetes/role/leninkart-role \
  bound_service_account_names=vault-auth \
  bound_service_account_namespaces=dev \
  policies=leninkart-policy \
  ttl=24h
```

Database secrets:
```bash
vault kv put secret/leninkart/product-service/database username="..." password="..."
vault kv put secret/leninkart/order-service/database username="..." password="..."
```

## Notes / follow-ups
- The current Vault config uses `tls_disable = 1` and `storage "file"`; this is dev-only.
- For production, enable TLS and use HA storage (Raft or cloud backend), plus auto-unseal.
- Avoid storing root tokens or unseal keys in Git or logs.
