from pathlib import Path
import re

ROOT = Path(".")

def replace(file, old, new):
    text = file.read_text()
    if old in text:
        file.write_text(text.replace(old, new))

def fix_frontend_service():
    f = ROOT / "helm/frontend/templates/service.yaml"
    replace(f,
        "targetPort: {{ .Values.service.port }}",
        "targetPort: http"
    )

def fix_frontend_deployment():
    f = ROOT / "helm/frontend/templates/deployment.yaml"
    text = f.read_text()
    if "name: http" not in text:
        text = text.replace(
            "ports:\n            - containerPort:",
            "ports:\n            - name: http\n              containerPort:"
        )
    text = re.sub(r"path: .*", "path: /", text)
    f.write_text(text)

def fix_order_service_selector():
    f = ROOT / "helm/order-service/templates/service.yaml"
    text = f.read_text()
    text = re.sub(
        r"selector:[\s\S]*?ports:",
        """selector:
    app.kubernetes.io/name: {{ include "order-service.name" . }}
    app.kubernetes.io/instance: {{ .Release.Name }}
  ports:""",
        text
    )
    f.write_text(text)

def fix_ingress():
    f = ROOT / "helm/ingress/templates/ingress.yaml"
    f.write_text("""apiVersion: networking.k8s.io/v1
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
""")

def main():
    fix_frontend_service()
    fix_frontend_deployment()
    fix_order_service_selector()
    fix_ingress()
    print("✅ LeninKart wiring normalized safely")

if __name__ == "__main__":
    main()