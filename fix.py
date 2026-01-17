import os

BASE_DIR = "k8s/postgres"
NAMESPACE = "dev"

POSTGRES_DB = "leninkart"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "postgres"
POSTGRES_IMAGE = "postgres:16"   # OFFICIAL, STABLE TAG

os.makedirs(BASE_DIR, exist_ok=True)

# ------------------ SECRET ------------------
secret_yaml = f"""apiVersion: v1
kind: Secret
metadata:
  name: postgres-secret
  namespace: {NAMESPACE}
type: Opaque
stringData:
  POSTGRES_DB: {POSTGRES_DB}
  POSTGRES_USER: {POSTGRES_USER}
  POSTGRES_PASSWORD: {POSTGRES_PASSWORD}
"""

# ------------------ STATEFULSET ------------------
statefulset_yaml = f"""apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: {NAMESPACE}
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: {POSTGRES_IMAGE}
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_DB
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_PASSWORD
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 8Gi
"""

# ------------------ SERVICE ------------------
service_yaml = f"""apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: {NAMESPACE}
spec:
  type: ClusterIP
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
"""

# Write files
files = {
    "postgres-secret.yaml": secret_yaml,
    "postgres-statefulset.yaml": statefulset_yaml,
    "postgres-service.yaml": service_yaml,
}

for filename, content in files.items():
    with open(os.path.join(BASE_DIR, filename), "w") as f:
        f.write(content)

print("✅ PostgreSQL manifests generated successfully!")
print("📂 Location: k8s/postgres/")
print("🚀 Ready for ArgoCD sync")