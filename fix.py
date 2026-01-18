import os
import shutil

BASE_DIR = os.getcwd()

def backup(path):
    if os.path.exists(path) and not path.endswith(".bak"):
        shutil.copy(path, path + ".bak")
        print(f"🧾 Backup created: {path}.bak")

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"✍️  Written: {path}")

# -------------------------------------------------
# Kafka Service (HEADLESS + controller port)
# -------------------------------------------------
def fix_kafka_service():
    path = "k8s/kafka/kafka-service.yaml"
    backup(path)

    content = """
apiVersion: v1
kind: Service
metadata:
  name: kafka
  namespace: dev
spec:
  clusterIP: None
  selector:
    app: kafka
  ports:
    - name: broker
      port: 9092
      targetPort: 9092
    - name: controller
      port: 9093
      targetPort: 9093
"""
    write_file(path, content)

# -------------------------------------------------
# Kafka StatefulSet (KRaft mode)
# -------------------------------------------------
def fix_kafka_statefulset():
    path = "k8s/kafka/kafka.yaml"
    backup(path)

    content = """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: kafka
  namespace: dev
spec:
  serviceName: kafka
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
            - containerPort: 9093
          env:
            # ---------------- KRaft Core ----------------
            - name: KAFKA_PROCESS_ROLES
              value: "broker,controller"

            - name: KAFKA_NODE_ID
              value: "0"

            - name: KAFKA_CONTROLLER_QUORUM_VOTERS
              value: "0@kafka-0.kafka.dev.svc.cluster.local:9093"

            # ---------------- Listeners ----------------
            - name: KAFKA_LISTENERS
              value: "PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093"

            - name: KAFKA_ADVERTISED_LISTENERS
              value: "PLAINTEXT://kafka-0.kafka.dev.svc.cluster.local:9092"

            - name: KAFKA_LISTENER_SECURITY_PROTOCOL_MAP
              value: "PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT"

            - name: KAFKA_CONTROLLER_LISTENER_NAMES
              value: "CONTROLLER"

            - name: KAFKA_INTER_BROKER_LISTENER_NAME
              value: "PLAINTEXT"

            # ---------------- Single-node settings ----------------
            - name: KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR
              value: "1"

            - name: KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR
              value: "1"

            - name: KAFKA_TRANSACTION_STATE_LOG_MIN_ISR
              value: "1"

            # ---------------- REQUIRED cluster id ----------------
            - name: CLUSTER_ID
              value: "leninkart-kafka-cluster-01"

            - name: KAFKA_LOG_DIRS
              value: "/var/lib/kafka/data"

          volumeMounts:
            - name: kafka-data
              mountPath: /var/lib/kafka/data

  volumeClaimTemplates:
    - metadata:
        name: kafka-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 5Gi
"""
    write_file(path, content)

# -------------------------------------------------
# Zookeeper warning (intentional)
# -------------------------------------------------
def warn_zookeeper():
    print("\n⚠️  IMPORTANT MANUAL STEP REQUIRED")
    print("🚫 ZooKeeper is no longer used in KRaft mode.")
    print("👉 You should DELETE these via Git or Argo prune:")
    print("   - k8s/kafka/zookeeper.yaml")
    print("   - k8s/kafka/zookeeper-service.yaml\n")

# -------------------------------------------------
def main():
    print("\n🔧 LeninKart Kafka KRaft Auto-Fix\n")

    fix_kafka_service()
    fix_kafka_statefulset()
    warn_zookeeper()

    print("✅ Kafka KRaft configuration applied")
    print("📌 Backups created with .bak")
    print("📌 NEXT: delete old Kafka PVC before sync\n")

    print("🚨 RUN THIS BEFORE ARGO SYNC:")
    print("kubectl delete pvc kafka-data-kafka-0 -n dev\n")

if __name__ == "__main__":
    main()