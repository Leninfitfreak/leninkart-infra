#!/bin/bash
# Vault Quick Start Script

set -e

echo "==================================================================="
echo "LeninKart Vault Quick Start"
echo "==================================================================="

# Check if Vault is running
echo "1. Checking Vault status..."
kubectl wait --for=condition=ready pod -l app=vault -n vault --timeout=120s

# Port forward
echo "2. Setting up port-forward..."
kubectl port-forward -n vault svc/vault 8200:8200 &
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
echo "  1. Configure Kubernetes auth: kubectl exec -n vault vault-0 -- /vault/policies/setup-k8s-auth.sh"
echo "  2. Store secrets: vault kv put secret/leninkart/..."
echo "  3. Check ExternalSecrets: kubectl get externalsecrets -n dev"
