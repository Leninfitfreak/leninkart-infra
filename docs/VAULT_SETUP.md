# HashiCorp Vault Setup Guide

## Overview

This guide explains how to set up and use HashiCorp Vault for secrets management in LeninKart.

## Architecture

```
┌─────────────────────────────────────────┐
│         Applications (dev)       │
│  ┌─────────────┐    ┌─────────────┐    │
│  │ Product Svc │    │ Order Svc   │    │
│  │  (reads)    │    │  (reads)    │    │
│  └──────┬──────┘    └──────┬──────┘    │
│         │                   │            │
│         └────────┬──────────┘            │
└──────────────────┼───────────────────────┘
                   │
          ┌────────▼─────────┐
          │ External Secrets │
          │    Operator      │
          └────────┬─────────┘
                   │
          ┌────────▼─────────┐
          │  HashiCorp Vault │
          │   (vault)       │
          └──────────────────┘
```

## Initial Setup

### 1. Deploy Vault

Vault is deployed automatically via ArgoCD. Check status:

```bash
kubectl get pods -n vault
kubectl logs -n vault vault-0
```

### 2. Initialize and Unseal Vault

**Important:** This is a one-time operation!

```bash
# Port-forward to Vault
kubectl port-forward -n vault svc/vault 8200:8200

# In another terminal, initialize Vault
export VAULT_ADDR='http://127.0.0.1:8200'
vault operator init -key-shares=1 -key-threshold=1

# Save the unseal key and root token!
# UNSEAL_KEY=...
# ROOT_TOKEN=...

# Unseal Vault
vault operator unseal <UNSEAL_KEY>

# Login
vault login <ROOT_TOKEN>
```

### 3. Configure Vault

```bash
# Enable KV secrets engine
vault secrets enable -version=2 -path=secret kv

# Enable Kubernetes authentication
vault auth enable kubernetes

# Get Kubernetes service account JWT
SA_JWT=$(kubectl get secret -n dev \
  $(kubectl get sa vault-auth -n dev -o jsonpath='{.secrets[0].name}') \
  -o jsonpath='{.data.token}' | base64 -d)

K8S_HOST=$(kubectl config view --raw --minify --flatten \
  -o jsonpath='{.clusters[0].cluster.server}')

# Configure Kubernetes auth
vault write auth/kubernetes/config \
  kubernetes_host="$K8S_HOST" \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
```

### 4. Create Policies and Roles

```bash
# Create policy
vault policy write leninkart-policy - <<EOF
path "secret/data/leninkart/*" {
  capabilities = ["read", "list"]
}
EOF

# Create Kubernetes role
vault write auth/kubernetes/role/leninkart-role \
  bound_service_account_names=vault-auth \
  bound_service_account_namespaces=dev \
  policies=leninkart-policy \
  ttl=24h
```

### 5. Store Secrets

```bash
# Database credentials
vault kv put secret/leninkart/product-service/database \
  username=product_user \
  password=your_secure_password_here

vault kv put secret/leninkart/order-service/database \
  username=order_user \
  password=your_secure_password_here

# Kafka credentials
vault kv put secret/leninkart/kafka/credentials \
  username=kafka_user \
  password=kafka_password

# Application configuration
vault kv put secret/leninkart/product-service/config \
  jwt_secret=your_jwt_secret \
  api_key=your_api_key

vault kv put secret/leninkart/order-service/config \
  jwt_secret=your_jwt_secret \
  api_key=your_api_key
```

## Using Secrets in Applications

### External Secrets Operator

ESO automatically syncs secrets from Vault to Kubernetes Secrets.

Check sync status:
```bash
kubectl get externalsecrets -n dev
kubectl describe externalsecret product-service-db-creds -n dev
```

### In Helm Charts

Update your deployment to use secrets:

```yaml
spec:
  containers:
    - name: app
      envFrom:
        - secretRef:
            name: product-service-db-secret
        - secretRef:
            name: product-service-config-secret
```

## Dynamic Database Credentials

Enable dynamic credentials (optional, advanced):

```bash
# Enable database secrets engine
vault secrets enable database

# Configure PostgreSQL
vault write database/config/leninkart-postgres \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@postgres.dev.svc.cluster.local:5432/leninkart" \
  username="postgres" \
  password="postgres"

# Create role
vault write database/roles/leninkart-app \
  db_name=leninkart-postgres \
  creation_statements="CREATE ROLE \"{{name}\}" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}\}";" \
  default_ttl="1h" \
  max_ttl="24h"

# Get dynamic credentials
vault read database/creds/leninkart-app
```

## Secret Rotation

### Manual Rotation
```bash
# Update secret in Vault
vault kv put secret/leninkart/product-service/database \
  username=new_user \
  password=new_password

# ESO will automatically sync within refreshInterval (default: 1h)
# Force immediate sync:
kubectl annotate externalsecret product-service-db-creds \
  force-sync="$(date +%s)" -n dev
```

### Automatic Rotation
Configure in ExternalSecret:
```yaml
spec:
  refreshInterval: 15m  # Sync every 15 minutes
```

## Troubleshooting

### Vault Pod Not Starting
```bash
kubectl logs -n vault vault-0
kubectl describe pod -n vault vault-0
```

### Vault is Sealed
```bash
kubectl exec -n vault vault-0 -- vault status
kubectl exec -n vault vault-0 -- vault operator unseal <KEY>
```

### ExternalSecret Not Syncing
```bash
kubectl get externalsecret -n dev
kubectl describe externalsecret <name> -n dev
kubectl logs -n external-secrets-system -l app.kubernetes.io/name=external-secrets
```

### Secret Not Available in Pod
```bash
kubectl get secret -n dev
kubectl describe secret product-service-db-secret -n dev
kubectl get externalsecret product-service-db-creds -n dev -o yaml
```

## Security Best Practices

1. **Never commit Vault tokens or unseal keys to Git**
2. **Use strong passwords for all secrets**
3. **Enable audit logging in production**
4. **Use proper storage backend in production (Consul, etc.)**
5. **Implement secret rotation policies**
6. **Restrict Vault policies to least privilege**
7. **Enable mTLS for Vault in production**

## Production Considerations

### High Availability
- Deploy 3+ Vault instances
- Use Consul or Raft for storage
- Configure auto-unseal with cloud KMS

### Backup
```bash
# Backup Vault data
vault operator raft snapshot save backup.snap
```

### Monitoring
- Enable audit logging
- Monitor seal status
- Track secret access patterns

## Access Vault UI

```bash
kubectl port-forward -n vault svc/vault-ui 8200:8200
```
Open: http://localhost:8200

## References

- [Vault Documentation](https://www.vaultproject.io/docs)
- [External Secrets Operator](https://external-secrets.io/)
- [Kubernetes Auth Method](https://www.vaultproject.io/docs/auth/kubernetes)
