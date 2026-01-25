from pathlib import Path

INGRESS_FILE = Path("helm/ingress/templates/ingress.yaml")

NEW_INGRESS = """\
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: leninkart-ingress
  namespace: {{ .Values.namespace }}
  annotations:
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      # -------- PRODUCT SERVICE --------
      - path: /api/products(/|$)(.*)
        pathType: ImplementationSpecific
        backend:
          service:
            name: leninkart-product-service
            port:
              number: 8081

      # -------- ORDER SERVICE --------
      - path: /api/orders(/|$)(.*)
        pathType: ImplementationSpecific
        backend:
          service:
            name: leninkart-order-service
            port:
              number: 8080

      # -------- FRONTEND --------
      - path: /
        pathType: Prefix
        backend:
          service:
            name: leninkart-frontend
            port:
              number: 80
"""

def main():
    if not INGRESS_FILE.exists():
        raise FileNotFoundError(f"Ingress template not found: {INGRESS_FILE}")

    backup = INGRESS_FILE.with_suffix(".yaml.bak")
    if not backup.exists():
        backup.write_text(INGRESS_FILE.read_text())
        print(f"🧾 Backup created: {backup}")

    INGRESS_FILE.write_text(NEW_INGRESS)
    print("✅ Ingress rewrite FIX applied safely")

    print("\n➡️ Next steps:")
    print("1. git commit -am 'fix: ingress rewrite for api paths'")
    print("2. git push origin dev")
    print("3. ArgoCD auto-sync")
    print("4. Test via minikube IP")

if __name__ == "__main__":
    main()