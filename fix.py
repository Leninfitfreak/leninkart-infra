from pathlib import Path
import shutil
import sys

INGRESS_FILE = Path("leninkart-ingress.yaml")

FIXED_INGRESS = """apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: leninkart-ingress
  namespace: dev
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

def backup_file():
    backup = INGRESS_FILE.with_suffix(".yaml.bak_auto")
    if not backup.exists():
        shutil.copy(INGRESS_FILE, backup)
        print(f"📦 Backup created: {backup}")

def fix_ingress():
    if not INGRESS_FILE.exists():
        print("❌ leninkart-ingress.yaml not found")
        sys.exit(1)

    backup_file()
    INGRESS_FILE.write_text(FIXED_INGRESS.strip() + "\n")
    print("✅ Ingress FIXED successfully")
    print("👉 Removed rewrite-target & regex")
    print("👉 API paths now match Spring Boot controllers")

if __name__ == "__main__":
    fix_ingress()