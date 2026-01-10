import os
import shutil
from pathlib import Path

ROOT = Path(".")
ARGO_DEV = ROOT / "argocd" / "applications" / "dev"
K8S_KAFKA = ROOT / "k8s" / "kafka"

def remove_path(p: Path):
    if p.exists():
        print(f"Removing: {p}")
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()

def cleanup():
    # Remove broken Bitnami kafka apps
    for f in ARGO_DEV.glob("kafka*.yaml"):
        remove_path(f)

    # Remove backup junk
    for root, dirs, files in os.walk(ROOT):
        for d in dirs:
            if "backup" in d or d.startswith(".auto"):
                remove_path(Path(root) / d)
        for f in files:
            if f.endswith(".bak"):
                remove_path(Path(root) / f)

def ensure_dirs():
    K8S_KAFKA.mkdir(parents=True, exist_ok=True)

def write_file(path: Path, content: str):
    print(f"Creating: {path}")
    path.write_text(content.strip() + "\n")

def create_zookeeper():
    write_file(
        K8S_KAFKA / "zookeeper.yaml",
        """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zookeeper
spec:
  replicas: 1
  selector:
    matchLabels:
      app: zookeeper
  template:
    metadata:
      labels:
        app: zookeeper
    spec:
      containers:
      - name: zookeeper
        image: confluentinc/cp-zookeeper:7.5.0
        ports:
        - containerPort: 2181
        env:
        - name: ZOOKEEPER_CLIENT_PORT
          value: "2181"
        - name: ZOOKEEPER_TICK_TIME
          value: "2000"
---
apiVersion: v1
kind: Service
metadata:
  name: zookeeper
spec:
  selector:
    app: zookeeper
  ports:
  - port: 2181
"""
    )

def create_kafka():
    write_file(
        K8S_KAFKA / "kafka.yaml",
        """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kafka
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kafka
  template:
    metadata:
      labels:
        app: kafka
    spec:
      containers:
      - name: kafka
        image: confluentinc/cp-kafka:7.5.0
        ports:
        - containerPort: 9092
        env:
        - name: KAFKA_BROKER_ID
          value: "1"
        - name: KAFKA_ZOOKEEPER_CONNECT
          value: "zookeeper:2181"
        - name: KAFKA_ADVERTISED_LISTENERS
          value: "PLAINTEXT://kafka:9092"
        - name: KAFKA_LISTENER_SECURITY_PROTOCOL_MAP
          value: "PLAINTEXT:PLAINTEXT"
        - name: KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR
          value: "1"
---
apiVersion: v1
kind: Service
metadata:
  name: kafka
spec:
  selector:
    app: kafka
  ports:
  - port: 9092
"""
    )

def create_argocd_app():
    write_file(
        ARGO_DEV / "kafka.yaml",
        """
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: dev-kafka
  namespace: argocd
spec:
  project: leninkart
  source:
    repoURL: https://github.com/Leninfitfreak/leninkart-infra.git
    targetRevision: dev
    path: k8s/kafka
  destination:
    server: https://kubernetes.default.svc
    namespace: dev
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
"""
    )

def main():
    print("=== Fixing Kafka (Confluent-based) ===")
    cleanup()
    ensure_dirs()
    create_zookeeper()
    create_kafka()
    create_argocd_app()
    print("✅ Kafka fixed using Confluent images")

if __name__ == "__main__":
    main()