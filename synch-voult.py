#!/usr/bin/env python3
"""
ArgoCD Vault Apps Sync Script (Pure Python)
============================================
Syncs Vault-related ArgoCD applications in correct order
"""

import subprocess
import time
import sys

def log(msg, color=""):
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "cyan": "\033[96m",
        "reset": "\033[0m"
    }
    color_code = colors.get(color, colors["reset"])
    print(f"{color_code}{msg}{colors['reset']}")

def run_cmd(cmd, capture=False, check=False):
    """Run command and return success status"""
    log(f"Running: {cmd}", "cyan")
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return result.stdout.strip() if result.returncode == 0 else None
        else:
            result = subprocess.run(cmd, shell=True, timeout=30)
            return result.returncode == 0
    except Exception as e:
        log(f"Error: {e}", "red")
        return False if not capture else None

log("=" * 70, "cyan")
log("ArgoCD Vault Stack Sync", "cyan")
log("=" * 70, "cyan")

# Step 1: Show current status
log("\n1. Current Application Status:", "green")
run_cmd("kubectl get applications -n argocd | findstr /I \"vault external\"")

# Step 2: Identify apps
log("\n2. Checking which Vault apps exist...", "green")

apps_to_sync = []

# Check for each possible app name
app_names = [
    "external-secrets-operator",
    "vault",
    "vault-dev",
    "vault-secretstores-dev",
    "vault-secretstore",
    "vault-externalsecrets"
]

for app_name in app_names:
    result = run_cmd(f"kubectl get application {app_name} -n argocd -o name 2>nul", capture=True)
    if result:
        log(f"  Found: {app_name}", "yellow")
        apps_to_sync.append(app_name)

if not apps_to_sync:
    log("No Vault apps found!", "red")
    sys.exit(1)

# Step 3: Ask to proceed
log(f"\n3. Found {len(apps_to_sync)} apps to sync", "green")
response = input("\nProceed with sync? (y/n): ")

if response.lower() != 'y':
    log("Sync cancelled", "yellow")
    sys.exit(0)

# Step 4: Check if argocd CLI is available
log("\n4. Checking for ArgoCD CLI...", "green")
argocd_available = run_cmd("argocd version 2>nul", capture=True)

if argocd_available:
    log("ArgoCD CLI found, using it", "green")
    use_cli = True
else:
    log("ArgoCD CLI not found, using kubectl", "yellow")
    use_cli = False

# Step 5: Sync apps in order
log("\n5. Syncing applications...", "green")

# Sync ESO first
if "external-secrets-operator" in apps_to_sync:
    log("\nSyncing External Secrets Operator...", "yellow")
    if use_cli:
        run_cmd("argocd app sync external-secrets-operator --force")
    else:
        run_cmd("kubectl patch application external-secrets-operator -n argocd --type merge -p '{\"operation\":{\"sync\":{}}}'")

    
    log("Waiting 30s for ESO to deploy...", "cyan")
    time.sleep(30)
    run_cmd("kubectl get pods -n external-secrets-system")

# Sync Vault
vault_app = None
for app in ["vault-dev", "vault"]:
    if app in apps_to_sync:
        vault_app = app
        break

if vault_app:
    log(f"\nSyncing {vault_app}...", "yellow")
    if use_cli:
        run_cmd(f"argocd app sync {vault_app} --force")
    else:
        run_cmd(f"kubectl patch application {vault_app} -n argocd --type merge -p '{{\"operation\":{{\"sync\":{{}}}}}}'")

    
    log("Waiting 20s for Vault to deploy...", "cyan")
    time.sleep(20)
    run_cmd("kubectl get pods -n vault")

# Sync SecretStore
secretstore_app = None
for app in ["vault-secretstores-dev", "vault-secretstore"]:
    if app in apps_to_sync:
        secretstore_app = app
        break

if secretstore_app:
    log(f"\nSyncing {secretstore_app}...", "yellow")
    if use_cli:
        run_cmd(f"argocd app sync {secretstore_app} --force")
    else:
        run_cmd(f"kubectl patch application {secretstore_app} -n argocd --type merge -p '{{\"operation\":{{\"sync\":{{}}}}}}'")

    
    log("Waiting 10s...", "cyan")
    time.sleep(10)

# Don't sync ExternalSecrets yet (needs Vault initialization)
if "vault-externalsecrets" in apps_to_sync:
    log("\nSkipping vault-externalsecrets (sync after Vault initialization)", "yellow")

# Step 6: Final status check
log("\n" + "=" * 70, "green")
log("SYNC COMPLETE - Checking Status", "green")
log("=" * 70, "green")

log("\nApplications:", "cyan")
run_cmd("kubectl get applications -n argocd | findstr /I \"vault external\"")

log("\nExternal Secrets Operator Pods:", "cyan")
run_cmd("kubectl get pods -n external-secrets-system")

log("\nVault Pods:", "cyan")
run_cmd("kubectl get pods -n vault")

log("\nSecretStore Resources:", "cyan")
result = run_cmd("kubectl get secretstore -n dev 2>nul", capture=True)
if result:
    print(result)
else:
    log("  (SecretStore CRD not installed yet)", "yellow")

# Step 7: Next steps
log("\n" + "=" * 70, "cyan")
log("NEXT STEPS", "cyan")
log("=" * 70, "cyan")

print("""
IF ALL PODS ARE RUNNING:

1. Initialize Vault (in separate terminal):
   kubectl port-forward -n vault svc/vault 8200:8200

2. In another terminal:
   $env:VAULT_ADDR='http://127.0.0.1:8200'
   vault operator init -key-shares=1 -key-threshold=1
   
   # Save output:
   # Unseal Key: xxx
   # Root Token: xxx
   
   vault operator unseal <UNSEAL_KEY>
   vault login <ROOT_TOKEN>

3. Configure Vault:
   vault secrets enable -version=2 -path=secret kv
   vault auth enable kubernetes
   
   vault write auth/kubernetes/config \\
     kubernetes_host="https://kubernetes.default.svc:443"
   
   vault policy write leninkart-policy - <<EOF
   path "secret/data/leninkart/*" {
     capabilities = ["read", "list"]
   }
   EOF
   
   vault write auth/kubernetes/role/leninkart-role \\
     bound_service_account_names=vault-auth \\
     bound_service_account_namespaces=dev \\
     policies=leninkart-policy \\
     ttl=24h

4. Store secrets:
   vault kv put secret/leninkart/product-service/database \\
     username=product_user \\
     password=SecurePassword123

   vault kv put secret/leninkart/order-service/database \\
     username=order_user \\
     password=SecurePassword456

5. Sync ExternalSecrets app:
   argocd app sync vault-externalsecrets
   # OR
   kubectl patch application vault-externalsecrets -n argocd --type merge -p '{"operation":{"sync":{}}}'

6. Verify:
   kubectl get externalsecrets -n dev
   kubectl get secrets -n dev | findstr service

TROUBLESHOOTING:

If apps still stuck:
  kubectl describe application external-secrets-operator -n argocd
  kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=50

If pods not starting:
  kubectl describe pod -n external-secrets-system <pod-name>
  kubectl describe pod -n vault vault-0
  kubectl logs -n vault vault-0

Access ArgoCD UI:
  kubectl port-forward -n argocd svc/argocd-server 8080:443
  # Get password:
  kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | python -m base64 -d
  # Open: https://localhost:8080 (username: admin)
""")

log("\nDone!", "green")