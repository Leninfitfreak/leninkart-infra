from pathlib import Path
import shutil
import yaml

ROOT = Path(".")
BACKUP = ROOT / ".backup_fix"
BACKUP.mkdir(exist_ok=True)

def backup(p):
    shutil.copy(p, BACKUP / p.name)

def write(p, data):
    with open(p, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)

print("\n🔧 LeninKart FINAL FIX (Confluent Kafka safe)\n")

# -------------------------------------------------
# 1️⃣ FIX order-service SERVICE SELECTOR
# -------------------------------------------------
svc = ROOT / "helm/order-service/templates/service.yaml"
backup(svc)

svc_yaml = {
    "apiVersion": "v1",
    "kind": "Service",
    "metadata": {"name": "order-service"},
    "spec": {
        "type": "{{ .Values.service.type }}",
        "selector": {
            "app.kubernetes.io/name": "order-service",
            "app.kubernetes.io/instance": "{{ .Release.Name }}"
        },
        "ports": [{
            "port": "{{ .Values.service.port }}",
            "targetPort": "http"
        }]
    }
}

with open(svc, "w") as f:
    f.write(
        "apiVersion: v1\n"
        "kind: Service\n"
        "metadata:\n"
        "  name: order-service\n"
        "spec:\n"
        "  type: {{ .Values.service.type }}\n"
        "  selector:\n"
        "    app.kubernetes.io/name: order-service\n"
        "    app.kubernetes.io/instance: {{ .Release.Name }}\n"
        "  ports:\n"
        "    - port: {{ .Values.service.port }}\n"
        "      targetPort: http\n"
    )

print("✅ order-service Service selector fixed")

# -------------------------------------------------
# 2️⃣ FIX order-service VALUES (Postgres DNS)
# -------------------------------------------------
values = ROOT / "helm/order-service/values-dev.yaml"
backup(values)

with open(values) as f:
    v = yaml.safe_load(f)

v["image"]["tag"] = str(v["image"]["tag"]).strip()
v["env"]["SPRING_DATASOURCE_URL"] = \
    "jdbc:postgresql://postgres-postgresql:5432/leninkart"

write(values, v)
print("✅ order-service Postgres hostname fixed")

# -------------------------------------------------
# 3️⃣ ADD KAFKA SERVICE (Confluent)
# -------------------------------------------------
kafka_svc = ROOT / "k8s/kafka/service.yaml"
if not kafka_svc.exists():
    kafka_service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "kafka",
            "namespace": "dev"
        },
        "spec": {
            "selector": {
                "app": "kafka"
            },
            "ports": [{
                "port": 9092,
                "targetPort": 9092
            }]
        }
    }
    write(kafka_svc, kafka_service)
    print("✅ Kafka Service created (Confluent)")

print("\n🎉 FIX COMPLETE — NO CONFUSION, NO EXTRA CHANGES")
print("📦 Backup stored in .backup_fix/")