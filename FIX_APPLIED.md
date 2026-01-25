# LeninKart Infrastructure - Auto-Fix Applied

## Fixes Applied by Script
- ✓ Fixed ingress rewrite-target issue

## Manual Steps Required

### 1. Commit and Push Changes
```bash
git add .
git commit -m "fix: resolve Kubernetes routing and service issues"
git push origin dev
```

### 2. Sync ArgoCD
Either wait for auto-sync or manually sync:
```bash
# Option A: ArgoCD CLI
argocd app sync leninkart-root

# Option B: ArgoCD UI
# Go to ArgoCD dashboard and click "Sync" on leninkart-root app
```

### 3. Access the Application
```bash
# Start minikube tunnel (required for LoadBalancer)
minikube tunnel

# In another terminal, get the service URL
minikube service leninkart-frontend -n dev --url

# Or use port-forward
kubectl port-forward -n dev svc/leninkart-frontend 8080:80
# Then access: http://localhost:8080
```

### 4. Verify Services
```bash
# Check all pods are running
kubectl get pods -n dev

# Check services
kubectl get svc -n dev

# Check ingress
kubectl get ingress -n dev

# Test backend directly
kubectl port-forward -n dev svc/leninkart-product-service 8081:8081
curl http://localhost:8081/api/products
```

### 5. Troubleshooting
If issues persist:

```bash
# Check product service logs
kubectl logs -n dev -l app=product-service --tail=100

# Check order service logs
kubectl logs -n dev -l app.kubernetes.io/name=order-service --tail=100

# Check frontend logs
kubectl logs -n dev -l app=frontend --tail=100

# Describe ingress for routing rules
kubectl describe ingress leninkart-ingress -n dev
```

## Errors Encountered
- No errors

## Backup Location
All original files backed up to: _backup_20260125_103645

## Need Help?
Check the interactive debugger for detailed guidance.
