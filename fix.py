import os
import shutil

ROOT = os.getcwd()

def backup(file):
    if os.path.exists(file) and not file.endswith(".bak"):
        shutil.copy(file, file + ".bak")

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

def fix_zookeeper_service():
    print("✔ Fixing Zookeeper Service")
    path = "k8s/kafka/zookeeper-service.yaml"

    content = """
apiVersion: v1
kind: Service
metadata:
  name: zookeeper
  namespace: dev
spec:
  clusterIP: None
  selector:
    app: zookeeper
  ports:
    - name: client
      port: 2181
      targetPort: 2181
"""
    write_file(path, content)

def fix_kafka_service_exists():
    print("✔ Validating Kafka Service")
    path = "k8s/kafka/kafka-service.yaml"
    if not os.path.exists(path):
        content = """
apiVersion: v1
kind: Service
metadata:
  name: kafka
  namespace: dev
spec:
  selector:
    app: kafka
  ports:
    - port: 9092
      targetPort: 9092
"""
        write_file(path, content)

def fix_order_service_probe():
    print("✔ Fixing Order-service startupProbe")

    path = "helm/order-service/values-dev.yaml"
    if not os.path.exists(path):
        print("⚠ order-service values-dev.yaml not found")
        return

    backup(path)

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    inside_startup = False

    for line in lines:
        if line.strip().startswith("startupProbe:"):
            inside_startup = True
            new_lines.append(line)
            continue

        if inside_startup:
            if "initialDelaySeconds" in line:
                new_lines.append("  initialDelaySeconds: 120\n")
                continue
            if "failureThreshold" in line:
                new_lines.append("  failureThreshold: 40\n")
                continue
            if line.startswith("readinessProbe"):
                inside_startup = False

        new_lines.append(line)

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def main():
    print("\n🔧 LeninKart DEV Infra Auto-Fix\n")

    fix_zookeeper_service()
    fix_kafka_service_exists()
    fix_order_service_probe()

    print("\n✅ DONE")
    print("📌 Helm templates were NOT YAML-parsed (correct)")
    print("📌 Backups created with .bak")
    print("📌 Commit and let ArgoCD sync\n")

if __name__ == "__main__":
    main()