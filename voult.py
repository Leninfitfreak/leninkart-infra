#!/usr/bin/env python3
"""
LeninKart HashiCorp Vault Integration
======================================
Implements secure secrets management using HashiCorp Vault

Features:
- Vault deployment in Kubernetes
- External Secrets Operator (ESO) integration
- Database credentials management
- Kafka credentials
- Application secrets
- Auto-rotation capabilities
"""

import os
from pathlib import Path

# ============================================
# Configuration
# ============================================

INFRA_REPO = Path(r"C:\Projects\infra\leninkart-infra")
NAMESPACE = "dev"
VAULT_NAMESPACE = "vault"
VAULT_VERSION = "1.15.4"
ESO_VERSION = "0.9.11"

# ============================================
# Helper Functions
# ============================================

def log(msg):
    print(f"[VAULT] {msg}")

def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    log(f"✓ {path}")

# ============================================
# 1. Vault Server Deployment
# ============================================

log("=" * 70)
log("Creating HashiCorp Vault Configuration")
log("=" * 70)

vault_dir = INFRA_REPO / "k8s" / "vault"

# Namespace
write_file(vault_dir / "00-namespace.yaml", f"""apiVersion: v1
kind: Namespace
metadata:
  name: {VAULT_NAMESPACE}
""")

# Service Account
write_file(vault_dir / "01-serviceaccount.yaml", f"""apiVersion: v1
kind: ServiceAccount
metadata:
  name: vault
  namespace: {VAULT_NAMESPACE}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: vault-server-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:auth-delegator
subjects:
  - kind: ServiceAccount
    name: vault
    namespace: {VAULT_NAMESPACE}
""")

# ConfigMap for Vault configuration
write_file(vault_dir / "02-configmap.yaml", f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: vault-config
  namespace: {VAULT_NAMESPACE}
data:
  vault-config.hcl: |
    ui = true
    
    listener "tcp" {{
      address = "0.0.0.0:8200"
      tls_disable = 1
    }}
    
    storage "file" {{
      path = "/vault/data"
    }}
    
    # Development mode - for production use proper storage backend
    disable_mlock = true
""")

# StatefulSet
write_file(vault_dir / "03-statefulset.yaml", f"""apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: vault
  namespace: {VAULT_NAMESPACE}
  labels:
    app: vault
spec:
  serviceName: vault
  replicas: 1
  selector:
    matchLabels:
      app: vault
  template:
    metadata:
      labels:
        app: vault
    spec:
      serviceAccountName: vault
      containers:
        - name: vault
          image: hashicorp/vault:{VAULT_VERSION}
          args:
            - "server"
            - "-config=/vault/config/vault-config.hcl"
          env:
            - name: VAULT_ADDR
              value: "http://127.0.0.1:8200"
            - name: VAULT_API_ADDR
              value: "http://vault.{VAULT_NAMESPACE}.svc.cluster.local:8200"
            - name: SKIP_CHOWN
              value: "true"
            - name: SKIP_SETCAP
              value: "true"
          ports:
            - name: http
              containerPort: 8200
              protocol: TCP
            - name: cluster
              containerPort: 8201
              protocol: TCP
          volumeMounts:
            - name: config
              mountPath: /vault/config
            - name: data
              mountPath: /vault/data
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /v1/sys/health?standbyok=true
              port: 8200
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /v1/sys/health?standbyok=true&uninitcode=204
              port: 8200
            initialDelaySeconds: 10
            periodSeconds: 5
      volumes:
        - name: config
          configMap:
            name: vault-config
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 1Gi
""")

# Service
write_file(vault_dir / "04-service.yaml", f"""apiVersion: v1
kind: Service
metadata:
  name: vault
  namespace: {VAULT_NAMESPACE}
  labels:
    app: vault
spec:
  type: ClusterIP
  selector:
    app: vault
  ports:
    - name: http
      port: 8200
      targetPort: 8200
    - name: cluster
      port: 8201
      targetPort: 8201
---
apiVersion: v1
kind: Service
metadata:
  name: vault-ui
  namespace: {VAULT_NAMESPACE}
  labels:
    app: vault
spec:
  type: ClusterIP
  selector:
    app: vault
  ports:
    - name: http
      port: 8200
      targetPort: 8200
""")

# Vault initialization script
write_file(vault_dir / "05-init-job.yaml", f"""apiVersion: batch/v1
kind: Job
metadata:
  name: vault-init
  namespace: {VAULT_NAMESPACE}
spec:
  template:
    metadata:
      labels:
        app: vault-init
    spec:
      serviceAccountName: vault
      restartPolicy: OnFailure
      containers:
        - name: vault-init
          image: hashicorp/vault:{VAULT_VERSION}
          env:
            - name: VAULT_ADDR
              value: "http://vault.{VAULT_NAMESPACE}.svc.cluster.local:8200"
          command:
            - /bin/sh
            - -c
            - |
              set -e
              echo "Waiting for Vault to be ready..."
              sleep 10
              
              # Check if Vault is already initialized
              if vault status 2>&1 | grep -q "Vault is sealed"; then
                echo "Vault is already initialized"
                exit 0
              fi
              
              # Initialize Vault
              echo "Initializing Vault..."
              vault operator init -key-shares=1 -key-threshold=1 -format=json > /tmp/vault-keys.json
              
              # Extract unseal key and root token
              UNSEAL_KEY=$(cat /tmp/vault-keys.json | grep -o '"unseal_keys_b64":\\[\"[^\"]*\"\\]' | cut -d'"' -f4)
              ROOT_TOKEN=$(cat /tmp/vault-keys.json | grep -o '"root_token":"[^"]*"' | cut -d'"' -f4)
              
              # Unseal Vault
              echo "Unsealing Vault..."
              vault operator unseal $UNSEAL_KEY
              
              # Login with root token
              vault login $ROOT_TOKEN
              
              # Enable KV secrets engine
              vault secrets enable -version=2 -path=secret kv
              
              # Enable Kubernetes auth
              vault auth enable kubernetes
              
              # Configure Kubernetes auth
              vault write auth/kubernetes/config \\
                kubernetes_host="https://kubernetes.default.svc:443"
              
              echo "Vault initialization complete!"
              echo "Root Token: $ROOT_TOKEN"
              echo "Unseal Key: $UNSEAL_KEY"
              echo ""
              echo "IMPORTANT: Save these credentials securely!"
              echo "For dev environment, they're also in /tmp/vault-keys.json"
""")

# ============================================
# 2. External Secrets Operator (ESO)
# ============================================

log("\n2. External Secrets Operator...")
eso_dir = INFRA_REPO / "k8s" / "external-secrets"

# ESO Installation via Helm values (for ArgoCD)
write_file(eso_dir / "external-secrets-values.yaml", f"""# External Secrets Operator Helm Values
installCRDs: true

replicaCount: 1

resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 200m
    memory: 256Mi

webhook:
  create: true

certController:
  create: true
""")

# SecretStore for Vault
write_file(eso_dir / "secretstore.yaml", f"""apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
  namespace: {NAMESPACE}
spec:
  provider:
    vault:
      server: "http://vault.{VAULT_NAMESPACE}.svc.cluster.local:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "leninkart-role"
          serviceAccountRef:
            name: vault-auth
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vault-auth
  namespace: {NAMESPACE}
""")

# ============================================
# 3. Vault Policies & Roles
# ============================================

log("\n3. Vault Policies & Roles...")
vault_config_dir = INFRA_REPO / "k8s" / "vault" / "policies"

# Policy for LeninKart services
write_file(vault_config_dir / "leninkart-policy.hcl", """# LeninKart Application Policy
path "secret/data/leninkart/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/leninkart/*" {
  capabilities = ["read", "list"]
}

path "database/creds/leninkart-*" {
  capabilities = ["read"]
}
""")

# Kubernetes role configuration script
write_file(vault_config_dir / "setup-k8s-auth.sh", f"""#!/bin/bash
# Script to configure Vault Kubernetes authentication

export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="<ROOT_TOKEN>"  # Replace with actual root token

# Create policy
vault policy write leninkart-policy /vault/policies/leninkart-policy.hcl

# Create Kubernetes role
vault write auth/kubernetes/role/leninkart-role \\
  bound_service_account_names=vault-auth \\
  bound_service_account_namespaces={NAMESPACE} \\
  policies=leninkart-policy \\
  ttl=24h
  
# Enable database secrets engine
vault secrets enable database

# Configure PostgreSQL dynamic secrets
vault write database/config/leninkart-postgres \\
  plugin_name=postgresql-database-plugin \\
  allowed_roles="leninkart-*" \\
  connection_url="postgresql://{{{{username}}}}:{{{{password}}}}@postgres.{NAMESPACE}.svc.cluster.local:5432/leninkart?sslmode=disable" \\
  username="postgres" \\
  password="postgres"

# Create database role for product-service
vault write database/roles/leninkart-product \\
  db_name=leninkart-postgres \\
  creation_statements="CREATE ROLE \\"{{{{name}}\}}" WITH LOGIN PASSWORD '{{{{password}}}}' VALID UNTIL '{{{{expiration}}}}'; \\
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \\"{{{{name}}}}\\"; \\
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO \\"{{{{name}}\}}";" \\
  default_ttl="1h" \\
  max_ttl="24h"

# Create database role for order-service
vault write database/roles/leninkart-order \\
  db_name=leninkart-postgres \\
  creation_statements="CREATE ROLE \\"{{{{name}}\}}" WITH LOGIN PASSWORD '{{{{password}}}}' VALID UNTIL '{{{{expiration}}}}'; \\
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \\"{{{{name}}}}\\"; \\
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO \\"{{{{name}}\}}";" \\
  default_ttl="1h" \\
  max_ttl="24h"

echo "Vault configuration complete!"
""")

# ============================================
# 4. Application Secrets with External Secrets
# ============================================

log("\n4. Application Secrets Configuration...")
secrets_dir = INFRA_REPO / "k8s" / "external-secrets" / "applications"

# PostgreSQL credentials for Product Service
write_file(secrets_dir / "product-service-db-secret.yaml", f"""apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: product-service-db-creds
  namespace: {NAMESPACE}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: product-service-db-secret
    creationPolicy: Owner
    template:
      engineVersion: v2
      data:
        SPRING_DATASOURCE_URL: "jdbc:postgresql://postgres.{NAMESPACE}.svc.cluster.local:5432/leninkart"
        SPRING_DATASOURCE_USERNAME: "{{{{ .username }}}}"
        SPRING_DATASOURCE_PASSWORD: "{{{{ .password }}}}"
  dataFrom:
    - extract:
        key: leninkart/product-service/database
---
# Static secret stored in Vault (for reference)
# kubectl exec -n vault vault-0 -- vault kv put secret/leninkart/product-service/database \\
#   username=product_user \\
#   password=secure_password_here
""")

# PostgreSQL credentials for Order Service
write_file(secrets_dir / "order-service-db-secret.yaml", f"""apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: order-service-db-creds
  namespace: {NAMESPACE}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: order-service-db-secret
    creationPolicy: Owner
    template:
      engineVersion: v2
      data:
        SPRING_DATASOURCE_URL: "jdbc:postgresql://postgres.{NAMESPACE}.svc.cluster.local:5432/leninkart"
        SPRING_DATASOURCE_USERNAME: "{{{{ .username }}}}"
        SPRING_DATASOURCE_PASSWORD: "{{{{ .password }}}}"
  dataFrom:
    - extract:
        key: leninkart/order-service/database
""")

# Kafka credentials
write_file(secrets_dir / "kafka-credentials.yaml", f"""apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: kafka-creds
  namespace: {NAMESPACE}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: kafka-secret
    creationPolicy: Owner
    template:
      engineVersion: v2
      data:
        KAFKA_BOOTSTRAP_SERVERS: "kafka-0.kafka.{NAMESPACE}.svc.cluster.local:9092"
        # Add SASL credentials when Kafka auth is enabled
        # KAFKA_SASL_USERNAME: "{{{{ .username }}}}"
        # KAFKA_SASL_PASSWORD: "{{{{ .password }}}}"
  dataFrom:
    - extract:
        key: leninkart/kafka/credentials
""")

# Application configuration secrets
write_file(secrets_dir / "app-config-secrets.yaml", f"""apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: product-service-config
  namespace: {NAMESPACE}
spec:
  refreshInterval: 30m
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: product-service-config-secret
    creationPolicy: Owner
  data:
    - secretKey: JWT_SECRET
      remoteRef:
        key: leninkart/product-service/config
        property: jwt_secret
    - secretKey: API_KEY
      remoteRef:
        key: leninkart/product-service/config
        property: api_key
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: order-service-config
  namespace: {NAMESPACE}
spec:
  refreshInterval: 30m
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: order-service-config-secret
    creationPolicy: Owner
  data:
    - secretKey: JWT_SECRET
      remoteRef:
        key: leninkart/order-service/config
        property: jwt_secret
    - secretKey: API_KEY
      remoteRef:
        key: leninkart/order-service/config
        property: api_key
""")

# ============================================
# 5. Update Helm Values for Secret Integration
# ============================================

log("\n5. Updating Helm values for Vault integration...")

# Note to add to Helm values
vault_helm_note = """
# ============================================
# VAULT SECRETS INTEGRATION
# ============================================
# Secrets are now managed by HashiCorp Vault via External Secrets Operator
# 
# To enable Vault secrets in deployments, add envFrom to your deployment:
#
# envFrom:
#   - secretRef:
#       name: product-service-db-secret
#   - secretRef:
#       name: product-service-config-secret
#
# This replaces hardcoded environment variables with Vault-managed secrets

secrets:
  vault:
    enabled: true
    secretStore: vault-backend
    refreshInterval: 1h
"""

product_values = INFRA_REPO / "helm" / "product-service" / "values-dev.yaml"
if product_values.exists():
    with open(product_values, 'a', newline='\n') as f:
        f.write(vault_helm_note)
    log(f"✓ Updated: product-service values")

order_values = INFRA_REPO / "helm" / "order-service" / "values-dev.yaml"
if order_values.exists():
    with open(order_values, 'a', newline='\n') as f:
        f.write(vault_helm_note)
    log(f"✓ Updated: order-service values")

# ============================================
# 6. ArgoCD Applications for Vault Stack
# ============================================

log("\n6. Creating ArgoCD Applications...")
argocd_dir = INFRA_REPO / "argocd" / "applications" / NAMESPACE

write_file(argocd_dir / "vault.yaml", f"""apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: vault-{NAMESPACE}
  namespace: argocd
spec:
  project: leninkart
  source:
    repoURL: https://github.com/Leninfitfreak/leninkart-infra.git
    targetRevision: dev
    path: k8s/vault
  destination:
    server: https://kubernetes.default.svc
    namespace: {VAULT_NAMESPACE}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
""")

write_file(argocd_dir / "external-secrets-operator.yaml", f"""apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: external-secrets-operator
  namespace: argocd
spec:
  project: leninkart
  source:
    repoURL: https://charts.external-secrets.io
    chart: external-secrets
    targetRevision: {ESO_VERSION}
    helm:
      valuesObject:
        installCRDs: true
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
  destination:
    server: https://kubernetes.default.svc
    namespace: external-secrets-system
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
""")

write_file(argocd_dir / "vault-secretstores.yaml", f"""apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: vault-secretstores-{NAMESPACE}
  namespace: argocd
spec:
  project: leninkart
  source:
    repoURL: https://github.com/Leninfitfreak/leninkart-infra.git
    targetRevision: dev
    path: k8s/external-secrets
  destination:
    server: https://kubernetes.default.svc
    namespace: {NAMESPACE}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
""")

# ============================================
# 7. Documentation
# ============================================

log("\n7. Creating documentation...")
docs_dir = INFRA_REPO / "docs"

write_file(docs_dir / "VAULT_SETUP.md", f"""# HashiCorp Vault Setup Guide

## Overview

This guide explains how to set up and use HashiCorp Vault for secrets management in LeninKart.

## Architecture

```
┌─────────────────────────────────────────┐
│         Applications ({NAMESPACE})       │
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
          │   ({VAULT_NAMESPACE})       │
          └──────────────────┘
```

## Initial Setup

### 1. Deploy Vault

Vault is deployed automatically via ArgoCD. Check status:

```bash
kubectl get pods -n {VAULT_NAMESPACE}
kubectl logs -n {VAULT_NAMESPACE} vault-0
```

### 2. Initialize and Unseal Vault

**Important:** This is a one-time operation!

```bash
# Port-forward to Vault
kubectl port-forward -n {VAULT_NAMESPACE} svc/vault 8200:8200

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
SA_JWT=$(kubectl get secret -n {NAMESPACE} \\
  $(kubectl get sa vault-auth -n {NAMESPACE} -o jsonpath='{{.secrets[0].name}}') \\
  -o jsonpath='{{.data.token}}' | base64 -d)

K8S_HOST=$(kubectl config view --raw --minify --flatten \\
  -o jsonpath='{{.clusters[0].cluster.server}}')

# Configure Kubernetes auth
vault write auth/kubernetes/config \\
  kubernetes_host="$K8S_HOST" \\
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
```

### 4. Create Policies and Roles

```bash
# Create policy
vault policy write leninkart-policy - <<EOF
path "secret/data/leninkart/*" {{
  capabilities = ["read", "list"]
}}
EOF

# Create Kubernetes role
vault write auth/kubernetes/role/leninkart-role \\
  bound_service_account_names=vault-auth \\
  bound_service_account_namespaces={NAMESPACE} \\
  policies=leninkart-policy \\
  ttl=24h
```

### 5. Store Secrets

```bash
# Database credentials
vault kv put secret/leninkart/product-service/database \\
  username=product_user \\
  password=your_secure_password_here

vault kv put secret/leninkart/order-service/database \\
  username=order_user \\
  password=your_secure_password_here

# Kafka credentials
vault kv put secret/leninkart/kafka/credentials \\
  username=kafka_user \\
  password=kafka_password

# Application configuration
vault kv put secret/leninkart/product-service/config \\
  jwt_secret=your_jwt_secret \\
  api_key=your_api_key

vault kv put secret/leninkart/order-service/config \\
  jwt_secret=your_jwt_secret \\
  api_key=your_api_key
```

## Using Secrets in Applications

### External Secrets Operator

ESO automatically syncs secrets from Vault to Kubernetes Secrets.

Check sync status:
```bash
kubectl get externalsecrets -n {NAMESPACE}
kubectl describe externalsecret product-service-db-creds -n {NAMESPACE}
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
vault write database/config/leninkart-postgres \\
  plugin_name=postgresql-database-plugin \\
  connection_url="postgresql://{{{{username}}}}:{{{{password}}}}@postgres.{NAMESPACE}.svc.cluster.local:5432/leninkart" \\
  username="postgres" \\
  password="postgres"

# Create role
vault write database/roles/leninkart-app \\
  db_name=leninkart-postgres \\
  creation_statements="CREATE ROLE \\"{{{{name}}\}}" WITH LOGIN PASSWORD '{{{{password}}}}' VALID UNTIL '{{{{expiration}}}}'; \\
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \\"{{{{name}}\}}";" \\
  default_ttl="1h" \\
  max_ttl="24h"

# Get dynamic credentials
vault read database/creds/leninkart-app
```

## Secret Rotation

### Manual Rotation
```bash
# Update secret in Vault
vault kv put secret/leninkart/product-service/database \\
  username=new_user \\
  password=new_password

# ESO will automatically sync within refreshInterval (default: 1h)
# Force immediate sync:
kubectl annotate externalsecret product-service-db-creds \\
  force-sync="$(date +%s)" -n {NAMESPACE}
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
kubectl logs -n {VAULT_NAMESPACE} vault-0
kubectl describe pod -n {VAULT_NAMESPACE} vault-0
```

### Vault is Sealed
```bash
kubectl exec -n {VAULT_NAMESPACE} vault-0 -- vault status
kubectl exec -n {VAULT_NAMESPACE} vault-0 -- vault operator unseal <KEY>
```

### ExternalSecret Not Syncing
```bash
kubectl get externalsecret -n {NAMESPACE}
kubectl describe externalsecret <name> -n {NAMESPACE}
kubectl logs -n external-secrets-system -l app.kubernetes.io/name=external-secrets
```

### Secret Not Available in Pod
```bash
kubectl get secret -n {NAMESPACE}
kubectl describe secret product-service-db-secret -n {NAMESPACE}
kubectl get externalsecret product-service-db-creds -n {NAMESPACE} -o yaml
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
kubectl port-forward -n {VAULT_NAMESPACE} svc/vault-ui 8200:8200
```
Open: http://localhost:8200

## References

- [Vault Documentation](https://www.vaultproject.io/docs)
- [External Secrets Operator](https://external-secrets.io/)
- [Kubernetes Auth Method](https://www.vaultproject.io/docs/auth/kubernetes)
""")

# Quick start script
write_file(INFRA_REPO / "scripts" / "vault-quickstart.sh", f"""#!/bin/bash
# Vault Quick Start Script

set -e

echo "==================================================================="
echo "LeninKart Vault Quick Start"
echo "==================================================================="

# Check if Vault is running
echo "1. Checking Vault status..."
kubectl wait --for=condition=ready pod -l app=vault -n {VAULT_NAMESPACE} --timeout=120s

# Port forward
echo "2. Setting up port-forward..."
kubectl port-forward -n {VAULT_NAMESPACE} svc/vault 8200:8200 &
PF_PID=$!
sleep 3

export VAULT_ADDR='http://127.0.0.1:8200'

# Check if initialized
if vault status 2>&1 | grep -q "Vault is not initialized"; then
  echo "3. Initializing Vault..."
  vault operator init -key-shares=1 -key-threshold=1 -format=json > vault-keys.json
  
  UNSEAL_KEY=$(cat vault-keys.json | jq -r '.unseal_keys_b64[0]')
  ROOT_TOKEN=$(cat vault-keys.json | jq -r '.root_token')
  
  echo "4. Unsealing Vault..."
  vault operator unseal $UNSEAL_KEY
  
  echo "5. Logging in..."
  vault login $ROOT_TOKEN
  
  echo ""
  echo "==================================================================="
  echo "IMPORTANT: Save these credentials!"
  echo "==================================================================="
  echo "Root Token: $ROOT_TOKEN"
  echo "Unseal Key: $UNSEAL_KEY"
  echo ""
  echo "Credentials also saved in: vault-keys.json"
  echo "==================================================================="
else
  echo "Vault already initialized"
fi

# Clean up
kill $PF_PID 2>/dev/null || true

echo ""
echo "✓ Vault setup complete!"
echo "Next steps:"
echo "  1. Configure Kubernetes auth: kubectl exec -n {VAULT_NAMESPACE} vault-0 -- /vault/policies/setup-k8s-auth.sh"
echo "  2. Store secrets: vault kv put secret/leninkart/..."
echo "  3. Check ExternalSecrets: kubectl get externalsecrets -n {NAMESPACE}"
""")

# ============================================
# Done
# ============================================

log("\n" + "=" * 70)
log("✓ VAULT CONFIGURATION COMPLETED!")
log("=" * 70)

print(f"""
VAULT INTEGRATION SUMMARY:

Created Files:
1. Vault StatefulSet & Services ({VAULT_NAMESPACE} namespace)
2. External Secrets Operator configuration
3. SecretStore for Vault backend
4. ExternalSecret definitions for all services
5. Vault policies and Kubernetes auth setup
6. ArgoCD applications for Vault stack
7. Documentation and quick-start scripts

NEXT STEPS:

1. Review changes:
   cd {INFRA_REPO}
   git status

2. Commit and push:
   git add .
   git commit -m "feat: add HashiCorp Vault secrets management"
   git push origin dev

3. Wait for ArgoCD to deploy Vault:
   kubectl get pods -n {VAULT_NAMESPACE} -w

4. Initialize Vault (ONE TIME):
   bash scripts/vault-quickstart.sh
   
   OR manually:
   kubectl port-forward -n {VAULT_NAMESPACE} svc/vault 8200:8200
   export VAULT_ADDR='http://127.0.0.1:8200'
   vault operator init
   vault operator unseal <KEY>
   vault login <TOKEN>

5. Configure Vault:
   kubectl exec -n {VAULT_NAMESPACE} vault-0 -- sh /vault/policies/setup-k8s-auth.sh

6. Store secrets:
   vault kv put secret/leninkart/product-service/database username=user password=pass
   vault kv put secret/leninkart/order-service/database username=user password=pass

7. Verify External Secrets sync:
   kubectl get externalsecrets -n {NAMESPACE}
   kubectl get secrets -n {NAMESPACE}

8. Access Vault UI:
   kubectl port-forward -n {VAULT_NAMESPACE} svc/vault-ui 8200:8200
   # Open: http://localhost:8200

IMPORTANT SECURITY NOTES:

⚠️  SAVE VAULT UNSEAL KEYS AND ROOT TOKEN SECURELY!
⚠️  Never commit credentials to Git
⚠️  Rotate secrets regularly
⚠️  Use proper storage backend in production (not file storage)
⚠️  Enable audit logging for compliance

Read full documentation: docs/VAULT_SETUP.md
""")