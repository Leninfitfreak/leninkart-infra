#!/usr/bin/env python3
"""
LeninKart Full Observability - FINAL VERSION FOR WINDOWS POWERSHELL
===================================================================
Paths from your screenshots:
- Services: C:\\Projects\\Services
- Infra: C:\\Projects\\infra\\leninkart-infra

This version:
- Uses PowerShell commands
- Correct paths from your VS Code screenshots
- Creates observability stack in infra repo
- Adds OTel config to Helm values (appends if not exists)
"""

import os
import sys
import subprocess
from pathlib import Path

# ============================================
# CONFIGURATION FROM YOUR SCREENSHOTS
# ============================================

INFRA_REPO = Path(r"C:\Projects\infra\leninkart-infra")
NAMESPACE = "dev"
GIT_BRANCH = "dev"
OTEL_VERSION = "0.92.0"
JAEGER_VERSION = "1.53"
PROMETHEUS_VERSION = "v2.48.1"
GRAFANA_VERSION = "10.2.3"
OTEL_AGENT_VERSION = "1.32.0"

# ============================================
# Helpers
# ============================================

def log(msg):
    print(f"[OBSERVABILITY] {msg}")

def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    log(f"✓ {path}")

# ============================================
# Create Manifests
# ============================================

log("=" * 70)
log("Creating Observability Stack")
log("=" * 70)

# 1. OTel Collector
log("\n1. OpenTelemetry Collector...")
otel_dir = INFRA_REPO / "k8s" / "otel"

write_file(otel_dir / "01-configmap.yaml", f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
  namespace: {NAMESPACE}
data:
  config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318
      zipkin:
        endpoint: 0.0.0.0:9411
    processors:
      batch: {{}}
      memory_limiter:
        limit_mib: 512
    exporters:
      otlp/jaeger:
        endpoint: jaeger-collector:4317
        tls:
          insecure: true
      prometheus:
        endpoint: 0.0.0.0:8889
      logging: {{}}
    service:
      pipelines:
        traces:
          receivers: [otlp, zipkin]
          processors: [batch]
          exporters: [otlp/jaeger, logging]
        metrics:
          receivers: [otlp]
          processors: [batch]
          exporters: [prometheus]
""")

write_file(otel_dir / "02-deployment.yaml", f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: {NAMESPACE}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
      annotations:
        sidecar.istio.io/inject: "false"
    spec:
      containers:
        - name: otel-collector
          image: otel/opentelemetry-collector-contrib:{OTEL_VERSION}
          args: ["--config=/conf/config.yaml"]
          ports:
            - containerPort: 4317
            - containerPort: 4318
            - containerPort: 9411
            - containerPort: 8889
          volumeMounts:
            - name: config
              mountPath: /conf
      volumes:
        - name: config
          configMap:
            name: otel-collector-config
---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: {NAMESPACE}
spec:
  selector:
    app: otel-collector
  ports:
    - name: otlp-grpc
      port: 4317
    - name: otlp-http
      port: 4318
    - name: zipkin
      port: 9411
    - name: metrics
      port: 8889
""")

# 2. Jaeger
log("2. Jaeger...")
jaeger_dir = INFRA_REPO / "k8s" / "jaeger"

write_file(jaeger_dir / "jaeger.yaml", f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
  namespace: {NAMESPACE}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jaeger
  template:
    metadata:
      labels:
        app: jaeger
      annotations:
        sidecar.istio.io/inject: "false"
    spec:
      containers:
        - name: jaeger
          image: jaegertracing/all-in-one:{JAEGER_VERSION}
          env:
            - name: COLLECTOR_OTLP_ENABLED
              value: "true"
          ports:
            - containerPort: 4317
            - containerPort: 16686
---
apiVersion: v1
kind: Service
metadata:
  name: jaeger-collector
  namespace: {NAMESPACE}
spec:
  selector:
    app: jaeger
  ports:
    - name: otlp
      port: 4317
---
apiVersion: v1
kind: Service
metadata:
  name: jaeger-query
  namespace: {NAMESPACE}
spec:
  selector:
    app: jaeger
  ports:
    - name: ui
      port: 16686
""")

# 3. Prometheus
log("3. Prometheus...")
prom_dir = INFRA_REPO / "k8s" / "prometheus"

write_file(prom_dir / "prometheus.yaml", f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: {NAMESPACE}
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
      - job_name: otel
        static_configs:
          - targets: [otel-collector:8889]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: {NAMESPACE}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
      annotations:
        sidecar.istio.io/inject: "false"
    spec:
      containers:
        - name: prometheus
          image: prom/prometheus:{PROMETHEUS_VERSION}
          ports:
            - containerPort: 9090
          volumeMounts:
            - name: config
              mountPath: /etc/prometheus
      volumes:
        - name: config
          configMap:
            name: prometheus-config
---
apiVersion: v1
kind: Service
metadata:
  name: prometheus
  namespace: {NAMESPACE}
spec:
  selector:
    app: prometheus
  ports:
    - port: 9090
""")

# 4. Grafana
log("4. Grafana...")
grafana_dir = INFRA_REPO / "k8s" / "grafana"

write_file(grafana_dir / "grafana.yaml", f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: {NAMESPACE}
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        url: http://prometheus:9090
        isDefault: true
      - name: Jaeger
        type: jaeger
        url: http://jaeger-query:16686
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: {NAMESPACE}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
      annotations:
        sidecar.istio.io/inject: "false"
    spec:
      containers:
        - name: grafana
          image: grafana/grafana:{GRAFANA_VERSION}
          ports:
            - containerPort: 3000
          env:
            - name: GF_AUTH_ANONYMOUS_ENABLED
              value: "true"
            - name: GF_AUTH_ANONYMOUS_ORG_ROLE
              value: "Admin"
          volumeMounts:
            - name: datasources
              mountPath: /etc/grafana/provisioning/datasources
      volumes:
        - name: datasources
          configMap:
            name: grafana-datasources
---
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: {NAMESPACE}
spec:
  selector:
    app: grafana
  ports:
    - port: 3000
""")

# 5. Istio
log("5. Istio Gateway & VirtualService...")
istio_dir = INFRA_REPO / "k8s" / "istio"

write_file(istio_dir / "gateway.yaml", f"""apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: leninkart-gateway
  namespace: {NAMESPACE}
spec:
  selector:
    istio: ingressgateway
  servers:
    - port:
        number: 80
        name: http
        protocol: HTTP
      hosts:
        - "*"
""")

write_file(istio_dir / "virtualservice.yaml", f"""apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: leninkart-routes
  namespace: {NAMESPACE}
spec:
  hosts:
    - "*"
  gateways:
    - leninkart-gateway
  http:
    - match:
        - uri:
            prefix: /api/products
      route:
        - destination:
            host: leninkart-product-service
            port:
              number: 8081
    - match:
        - uri:
            prefix: /api/orders
      route:
        - destination:
            host: leninkart-order-service
            port:
              number: 8080
    - match:
        - uri:
            prefix: /
      route:
        - destination:
            host: leninkart-frontend
            port:
              number: 80
""")

write_file(istio_dir / "telemetry.yaml", f"""apiVersion: telemetry.istio.io/v1alpha1
kind: Telemetry
metadata:
  name: leninkart-telemetry
  namespace: {NAMESPACE}
spec:
  tracing:
    - providers:
        - name: zipkin
      randomSamplingPercentage: 100.0
""")

# 6. ArgoCD Apps
log("6. ArgoCD Applications...")
argocd_dir = INFRA_REPO / "argocd" / "applications" / NAMESPACE

for app_name, path in [
    ("otel-collector", "k8s/otel"),
    ("jaeger", "k8s/jaeger"),
    ("prometheus", "k8s/prometheus"),
    ("grafana", "k8s/grafana"),
    ("istio-config", "k8s/istio"),
]:
    write_file(argocd_dir / f"{app_name}.yaml", f"""apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: {app_name}-{NAMESPACE}
  namespace: argocd
spec:
  project: leninkart
  source:
    repoURL: https://github.com/Leninfitfreak/leninkart-infra.git
    targetRevision: {GIT_BRANCH}
    path: {path}
  destination:
    server: https://kubernetes.default.svc
    namespace: {NAMESPACE}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
""")

# 7. Add OTel to Helm values (if they exist)
log("\n7. Updating Helm values...")

for service, port in [("product-service", "8081"), ("order-service", "8080")]:
    values_file = INFRA_REPO / "helm" / service / "values-dev.yaml"
    if values_file.exists():
        with open(values_file, 'r') as f:
            content = f.read()
        
        if "otel:" not in content:
            with open(values_file, 'a', newline='\n') as f:
                f.write(f"""

# ============================================
# OPENTELEMETRY CONFIGURATION
# ============================================
otel:
  enabled: true
  javaAgent:
    version: "{OTEL_AGENT_VERSION}"
  serviceName: "{service}"
  endpoint: "http://otel-collector:4318"

annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "{port}"
""")
            log(f"✓ Updated Helm values: {service}")
    else:
        log(f"⚠️  Helm values not found: {service}")

# Done
log("\n" + "=" * 70)
log("✓ COMPLETED!")
log("=" * 70)

print(f"""
NEXT STEPS:

1. Review changes:
   cd {INFRA_REPO}
   git status

2. Commit & push:
   git add .
   git commit -m "feat: add observability stack"
   git push origin {GIT_BRANCH}

3. Install Istio (if not done):
   # Download: https://github.com/istio/istio/releases/download/1.20.2/istio-1.20.2-win.zip
   istioctl install --set profile=demo -y
   kubectl label namespace {NAMESPACE} istio-injection=enabled --overwrite

4. Wait for ArgoCD sync (5 min):
   kubectl get pods -n {NAMESPACE} -w

5. Access tools:
   kubectl port-forward -n {NAMESPACE} svc/jaeger-query 16686:16686
   kubectl port-forward -n {NAMESPACE} svc/grafana 3000:3000

6. Test & view traces:
   minikube tunnel
   curl http://$(kubectl get svc -n istio-system istio-ingressgateway -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}')/api/products
""")