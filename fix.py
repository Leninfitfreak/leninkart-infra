from pathlib import Path
import shutil

ROOT = Path(".")

# ---- Paths ----
HELM_INGRESS = ROOT / "helm" / "ingress"
TEMPLATES = HELM_INGRESS / "templates"
ARGO_APP = ROOT / "argocd" / "applications" / "dev" / "ingress.yaml"
BACKUP_DIR = ROOT / "_ingress_backup"

OLD_INGRESS_FILES = [
    "leninkart-ingress.yaml",
    "leninkart-api-ingress.yaml",
    "leninkart-frontend-ingress.yaml"
]

# ---- Helpers ----
def backup_file(path: Path):
    BACKUP_DIR.mkdir(exist_ok=True)
    target = BACKUP_DIR / path.name
    if not target.exists():
        shutil.move(str(path), str(target))
        print(f"🗑️  Moved old ingress → {target}")
    else:
        print(f"⚠️  Backup already exists, skipping: {path.name}")

# ---- Step 1: Cleanup old ingress ----
def cleanup_old_ingress():
    print("🔍 Cleaning legacy ingress manifests...")
    for name in OLD_INGRESS_FILES:
        path = ROOT / name
        if path.exists():
            backup_file(path)

# ---- Step 2: Create Helm ingress chart ----
def create_helm_chart():
    print("📦 Creating Helm ingress chart...")

    if HELM_INGRESS.exists():
        print("⚠️  helm/ingress already exists — skipping creation")
        return

    TEMPLATES.mkdir(parents=True, exist_ok=True)

    (HELM_INGRESS / "Chart.yaml").write_text(
"""apiVersion: v2
name: ingress
description: LeninKart Ingress
type: application
version: 0.1.0
"""
    )

    (HELM_INGRESS / "values-dev.yaml").write_text(
"""namespace: dev
"""
    )

    (TEMPLATES / "ingress.yaml").write_text(
"""apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: leninkart-ingress
  namespace: {{ .Values.namespace }}
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /api/products
        pathType: Prefix
        backend:
          service:
            name: leninkart-product-service
            port:
              number: 8081

      - path: /api/orders
        pathType: Prefix
        backend:
          service:
            name: leninkart-order-service
            port:
              number: 8080

      - path: /
        pathType: Prefix
        backend:
          service:
            name: leninkart-frontend
            port:
              number: 80
"""
    )

    print("✅ Helm ingress chart created")

# ---- Step 3: Create ArgoCD Application ----
def create_argocd_app():
    print("🧭 Creating ArgoCD ingress application...")

    if ARGO_APP.exists():
        print("⚠️  ArgoCD ingress app already exists — skipping")
        return

    ARGO_APP.write_text(
"""apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: dev-ingress
  namespace: argocd
spec:
  project: leninkart
  source:
    repoURL: https://github.com/Leninfitfreak/leninkart-infra.git
    targetRevision: dev
    path: helm/ingress
    helm:
      valueFiles:
        - values-dev.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: dev
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
"""
    )

    print("✅ ArgoCD ingress application created")

# ---- Main ----
def main():
    print("🚀 Enabling GitOps-managed Ingress (SAFE MODE)")
    cleanup_old_ingress()
    create_helm_chart()
    create_argocd_app()
    print("\n✅ DONE")
    print("➡️ Commit & push to dev branch")
    print("➡️ ArgoCD will reconcile ingress automatically")

if __name__ == "__main__":
    main()