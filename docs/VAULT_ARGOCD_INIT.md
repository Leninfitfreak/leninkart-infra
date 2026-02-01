# Vault ArgoCD Initialization Guide

## Overview

This guide explains how to initialize Vault after ArgoCD deployment.

## Deployment Order (via sync-wave)

ArgoCD will deploy in this order:
1. **Wave 1**: External Secrets Operator (ESO)
2. **Wave 2**: Vault StatefulSet
3. **Wave 3**: SecretStore (connects dev namespace to Vault)
4. **Wave 4**: ExternalSecrets (creates K8s secrets from Vault) - Manual sync initially

## Step-by-Step Initialization

### 1. Commit and Push Changes

```powershell
cd C:\Projects\infra\leninkart-infra
git add argocd/ k8s/
git commit -m "feat: add ArgoCD apps for Vault stack"
git push origin dev
```

### 2. Watch ArgoCD Deploy

```powershell
# Watch applications
kubectl get applications -n argocd -w

# Or in ArgoCD UI
# http://localhost:8080 (if port-forwarded)
```

**Expected order:**
- `external-secrets-operator` syncs first (wave 1)
- `vault` syncs next (wave 2)
- `vault-secretstore` syncs next (wave 3)
- `vault-externalsecrets` appears but won't auto-sync (wave 4)

### 3. Verify Pods are Running

```powershell
# Check ESO
kubectl get pods -n external-secrets-system

# Expected: external-secrets-xxx Running

# Check Vault
kubectl get pods -n vault

# Expected: vault-0 Running (but sealed)
```

### 4. Initialize Vault (ONE-TIME)

**Port-forward to Vault:**
```powershell
kubectl port-forward -n vault svc/vault 8200:8200
```

**In another PowerShell window:**
```powershell
# Set environment
$env:VAULT_ADDR='http://127.0.0.1:8200'

# Check status
vault status
# Should show: Initialized: false, Sealed: true

# Initialize Vault
vault operator init -key-shares=1 -key-threshold=1 -format=json > vault-keys.json

# Extract keys
$vaultKeys = Get-Content vault-keys.json | ConvertFrom-Json
$unsealKey = $vaultKeys.unseal_keys_b64[0]
$rootToken = $vaultKeys.root_token

Write-Host "Unseal Key: $unsealKey"
Write-Host "Root Token: $rootToken"

# SAVE THESE SECURELY!

# Unseal Vault
vault operator unseal $unsealKey

# Login
vault login $rootToken

# Verify
vault status
# Should show: Initialized: true, Sealed: false
```

### 5. Configure Vault

```powershell
# Still in the PowerShell window with VAULT_ADDR set

# Enable KV secrets engine
vault secrets enable -version=2 -path=secret kv

# Enable Kubernetes authentication
vault auth enable kubernetes

# Get Kubernetes config
kubectl exec -n vault vault-0 -- sh -c 'cat /var/run/secrets/kubernetes.io/serviceaccount/token' > sa-token.txt
kubectl exec -n vault vault-0 -- sh -c 'cat /var/run/secrets/kubernetes.io/serviceaccount/ca.crt' > ca.crt

# Configure Kubernetes auth
vault write auth/kubernetes/config `
  kubernetes_host="https://kubernetes.default.svc:443" `
  kubernetes_ca_cert=@ca.crt

# Create policy
vault policy write leninkart-policy - <<EOF
path "secret/data/leninkart/*" {
  capabilities = ["read", "list"]
}
path "secret/metadata/leninkart/*" {
  capabilities = ["read", "list"]
}
EOF

# Create Kubernetes role
vault write auth/kubernetes/role/leninkart-role `
  bound_service_account_names=vault-auth `
  bound_service_account_namespaces=dev `
  policies=leninkart-policy `
  ttl=24h
```

### 6. Store Secrets in Vault

```powershell
# Database credentials
vault kv put secret/leninkart/product-service/database `
  username=product_user `
  password=SecurePassword123!

vault kv put secret/leninkart/order-service/database `
  username=order_user `
  password=SecurePassword456!

# Kafka credentials
vault kv put secret/leninkart/kafka/credentials `
  username=kafka_user `
  password=KafkaPassword789!

# Application config
vault kv put secret/leninkart/product-service/config `
  jwt_secret=MyJWTSecret123 `
  api_key=MyAPIKey456

vault kv put secret/leninkart/order-service/config `
  jwt_secret=MyJWTSecret123 `
  api_key=MyAPIKey456

# Verify secrets are stored
vault kv list secret/leninkart
```

### 7. Enable ExternalSecrets Sync

Now that Vault is initialized and has secrets, enable the ExternalSecrets app:

**Option A: Via ArgoCD UI**
1. Go to ArgoCD UI
2. Find `vault-externalsecrets` application
3. Click "APP DETAILS" → "SYNC POLICY"
4. Enable "AUTO-SYNC"
5. Click "SYNC" button

**Option B: Via kubectl**
```powershell
kubectl patch application vault-externalsecrets -n argocd --type merge -p '{
  "spec": {
    "syncPolicy": {
      "automated": {
        "prune": true,
        "selfHeal": true
      }
    }
  }
}'

# Trigger sync
argocd app sync vault-externalsecrets
```

### 8. Verify ExternalSecrets

```powershell
# Check ExternalSecret resources
kubectl get externalsecrets -n dev

# Expected output:
# NAME                          STORE           REFRESH   STATUS
# product-service-db-creds      vault-backend   1h        SecretSynced
# order-service-db-creds        vault-backend   1h        SecretSynced
# kafka-creds                   vault-backend   1h        SecretSynced

# Check created Kubernetes Secrets
kubectl get secrets -n dev | findstr service

# Describe a secret to verify content
kubectl describe secret product-service-db-secret -n dev
```

### 9. Update Application Deployments

Update your Helm deployment templates to use the Vault-managed secrets:

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

## Troubleshooting

### Vault Pod in CrashLoopBackOff
```powershell
kubectl logs -n vault vault-0
kubectl describe pod -n vault vault-0
```

### Vault Sealed After Restart
```powershell
kubectl exec -n vault vault-0 -- vault operator unseal <UNSEAL_KEY>
```

### ExternalSecret Not Syncing
```powershell
kubectl describe externalsecret product-service-db-creds -n dev
kubectl logs -n external-secrets-system -l app.kubernetes.io/name=external-secrets
```

### SecretStore Authentication Failed
```powershell
# Check service account
kubectl get sa vault-auth -n dev

# Check Vault role
vault read auth/kubernetes/role/leninkart-role

# Test authentication
kubectl exec -n dev -it <pod-name> -- sh
cat /var/run/secrets/kubernetes.io/serviceaccount/token
```

## Unsealing Vault Automatically (Optional)

For production, consider using auto-unseal with cloud KMS:
- AWS KMS
- Azure Key Vault
- GCP Cloud KMS

For dev, you can create a Job to unseal on startup (not recommended for prod):

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: vault-unseal
  namespace: vault
spec:
  template:
    spec:
      containers:
        - name: unseal
          image: hashicorp/vault:1.15.4
          env:
            - name: VAULT_ADDR
              value: "http://vault:8200"
            - name: UNSEAL_KEY
              valueFrom:
                secretKeyRef:
                  name: vault-unseal-key
                  key: unseal-key
          command:
            - sh
            - -c
            - vault operator unseal $UNSEAL_KEY
      restartPolicy: OnFailure
```

## Access Vault UI

```powershell
kubectl port-forward -n vault svc/vault-ui 8200:8200
```

Open: http://localhost:8200

Login with root token.

## Monitoring

Add to your Prometheus scrape configs:

```yaml
- job_name: 'vault'
  static_configs:
    - targets: ['vault.vault.svc.cluster.local:8200']
```

## Backup

```powershell
# Create snapshot (Raft storage)
kubectl exec -n vault vault-0 -- vault operator raft snapshot save /tmp/vault-backup.snap

# Copy to local
kubectl cp vault/vault-0:/tmp/vault-backup.snap ./vault-backup-$(date +%Y%m%d).snap
```
