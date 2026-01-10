import yaml
import shutil
from pathlib import Path

KAFKA_IMAGE = "confluentinc/cp-kafka"
KAFKA_TAG = "7.6.0"

ZK_IMAGE = "confluentinc/cp-zookeeper"
ZK_TAG = "7.6.0"


def backup(path: Path):
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy(path, bak)
    print(f"✔ Backup created: {bak}")


def update(obj):
    if isinstance(obj, dict):
        # Helm-style image block
        if "image" in obj and isinstance(obj["image"], dict):
            repo = obj["image"].get("repository", "")
            if "kafka" in repo:
                obj["image"]["repository"] = KAFKA_IMAGE
                obj["image"]["tag"] = KAFKA_TAG
                obj["image"]["pullPolicy"] = "IfNotPresent"

            if "zookeeper" in repo:
                obj["image"]["repository"] = ZK_IMAGE
                obj["image"]["tag"] = ZK_TAG
                obj["image"]["pullPolicy"] = "IfNotPresent"

        # Pod spec
        if "containers" in obj:
            for c in obj["containers"]:
                img = c.get("image", "")
                if "kafka" in img:
                    c["image"] = f"{KAFKA_IMAGE}:{KAFKA_TAG}"
                    c["imagePullPolicy"] = "IfNotPresent"
                if "zookeeper" in img:
                    c["image"] = f"{ZK_IMAGE}:{ZK_TAG}"
                    c["imagePullPolicy"] = "IfNotPresent"

        for v in obj.values():
            update(v)

    elif isinstance(obj, list):
        for i in obj:
            update(i)


def main():
    files = [
        p for p in Path(".").rglob("*.yaml")
        if "kafka" in p.name.lower() or "zookeeper" in p.name.lower()
    ]

    if not files:
        print("❌ No Kafka/Zookeeper YAML files found")
        return

    for f in files:
        print(f"\n🔧 Updating: {f}")
        backup(f)

        with open(f) as fh:
            data = yaml.safe_load(fh)

        update(data)

        with open(f, "w") as fh:
            yaml.safe_dump(data, fh, sort_keys=False)

        print("✅ Updated")

    print("\n🎉 Kafka image update complete (Confluent, Docker Hub)")


if __name__ == "__main__":
    main()