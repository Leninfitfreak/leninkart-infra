import os
import shutil
import yaml
from datetime import datetime

ROOT = os.getcwd()
BACKUP_DIR = os.path.join(ROOT, f".backup_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

FILES_TO_FIX = [
    "helm/order-service/values-dev.yaml",
    "helm/product-service/values-dev.yaml",
]

def backup_file(path):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dst = os.path.join(BACKUP_DIR, path.replace("/", "_"))
    shutil.copy2(path, dst)

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def save_yaml(path, data):
    with open(path, "w") as f:
        yaml.dump(data, f, sort_keys=False)

def fix_order_service(values):
    # Fix image tag
    if "image" in values:
        tag = values["image"].get("tag", "")
        if tag.endswith("-"):
            values["image"]["tag"] = tag.rstrip("-")

    # Ensure service block
    values.setdefault("service", {})
    values["service"].setdefault("type", "ClusterIP")
    values["service"].setdefault("port", 8080)

    # Ensure env vars
    env = values.setdefault("env", {})

    env["SPRING_DATASOURCE_URL"] = (
        "jdbc:postgresql://postgres-postgresql.dev.svc.cluster.local:5432/leninkart"
    )
    env["SPRING_DATASOURCE_USERNAME"] = "postgres"
    env["SPRING_DATASOURCE_PASSWORD"] = "root123"
    env["SPRING_JPA_DATABASE_PLATFORM"] = "org.hibernate.dialect.PostgreSQLDialect"
    env["SPRING_JPA_HIBERNATE_DDL_AUTO"] = "update"
    env["SPRING_DATASOURCE_HIKARI_INITIALIZATION_FAIL_TIMEOUT"] = "60000"
    env["SPRING_KAFKA_BOOTSTRAP_SERVERS"] = "kafka.dev.svc.cluster.local:9092"

def fix_product_service(values):
    values.setdefault("service", {})
    values["service"].setdefault("type", "ClusterIP")
    values["service"].setdefault("port", 8081)

def main():
    print("🔧 Starting LeninKart auto-fix...")
    print(f"📦 Backup directory: {BACKUP_DIR}")

    for rel_path in FILES_TO_FIX:
        path = os.path.join(ROOT, rel_path)
        if not os.path.exists(path):
            print(f"⚠️ Skipping missing file: {rel_path}")
            continue

        backup_file(path)
        values = load_yaml(path)

        if "order-service" in rel_path:
            fix_order_service(values)
            print(f"✅ Fixed order-service: {rel_path}")

        if "product-service" in rel_path:
            fix_product_service(values)
            print(f"✅ Fixed product-service: {rel_path}")

        save_yaml(path, values)

    print("\n✅ ALL FIXES APPLIED SUCCESSFULLY")
    print("➡️ Next steps:")
    print("   1. git status")
    print("   2. git commit -am \"fix: postgres, image tag, helm values\"")
    print("   3. git push")
    print("   4. Sync ArgoCD")

if __name__ == "__main__":
    main()