import os
import shutil

KAFKA_FILE = "k8s/kafka/kafka.yaml"
ZK_FILES = [
    "k8s/kafka/zookeeper.yaml",
    "k8s/kafka/zookeeper-service.yaml"
]

def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + ".bak")

def remove_zookeeper():
    for f in ZK_FILES:
        if os.path.exists(f):
            print(f"❌ Removing {f}")
            backup(f)
            os.remove(f)

def write_kraft_kafka():
    print("✅ Writing PURE KRaft Kafka manifest")

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
            - name: KAFKA_PROCESS_ROLES
              value: "controller,broker"

            - name: KAFKA_NODE_ID
              value: "0"

            - name: KAFKA_CLUSTER_ID
              value: "MkU3OEVBNTcwNTJENDM2Qk"

            - name: KAFKA_CONTROLLER_QUORUM_VOTERS
              value: "0@kafka-0.kafka.dev.svc.cluster.local:9093"

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
    with open(KAFKA_FILE, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

def main():
    print("\n🔥 Converting LeninKart Kafka to PURE KRaft mode\n")
    remove_zookeeper()
    write_kraft_kafka()
    print("\n✅ DONE: Pure KRaft, no ZooKeeper, no hybrid\n")

if __name__ == "__main__":
    main()