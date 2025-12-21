import os
import yaml
from copy import deepcopy

BASE_DIR = "helm"

SERVICES = {
    "frontend": {
        "service_port": 3000,
        "container_port": 3000,
        "readiness_path": "/",
        "liveness_path": "/",
        "env": []
    },
    "order-service": {
        "service_port": 8080,
        "container_port": 8080,
        "readiness_path": "/actuator/health",
        "liveness_path": "/actuator/health",
        "env": [
            {"name": "SPRING_DATASOURCE_URL", "value": "jdbc:mysql://mysql.dev.svc.cluster.local:3306/leninkart"},
            {"name": "SPRING_DATASOURCE_USERNAME", "value": "root"},
            {"name": "SPRING_DATASOURCE_PASSWORD", "value": "root123"},
            {"name": "SPRING_KAFKA_BOOTSTRAP_SERVERS", "value": "kafka.dev.svc.cluster.local:9092"}
        ]
    },
    "product-service": {
        "service_port": 8080,
        "container_port": 8080,
        "readiness_path": "/actuator/health",
        "liveness_path": "/actuator/health",
        "env": []
    }
}

BASE_TEMPLATE = {
    "replicaCount": 1,
    "image": {
        "repository": "",
        "pullPolicy": "IfNotPresent",
        "tag": "will-be-overwritten-by-ci"
    },
    "service": {
        "type": "ClusterIP",
        "port": None
    },
    "containerPort": None,
    "resources": {
        "requests": {"cpu": "100m", "memory": "128Mi"},
        "limits": {"cpu": "300m", "memory": "256Mi"}
    },
    "readinessProbe": {},
    "livenessProbe": {}
}

def write_yaml(path, data):
    with open(path, "w") as f:
        yaml.dump(data, f, sort_keys=False)

def load_yaml(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return yaml.safe_load(f)

def fix_service(service, config):
    svc_dir = os.path.join(BASE_DIR, service)
    dev_file = os.path.join(svc_dir, "values-dev.yaml")

    print(f"\n🔧 Processing {service}")

    values = load_yaml(dev_file)
    if values is None:
        print("  ➕ values-dev.yaml missing, creating new one")
        values = deepcopy(BASE_TEMPLATE)

    # Image
    values.setdefault("image", {})
    values["image"]["repository"] = f"asia-south1-docker.pkg.dev/leninkart-478305/leninkart/{service}"
    values["image"]["tag"] = "will-be-overwritten-by-ci"

    # Service + Port
    values.setdefault("service", {})
    values["service"]["type"] = "ClusterIP"
    values["service"]["port"] = config["service_port"]
    values["containerPort"] = config["container_port"]

    # Probes
    values["readinessProbe"] = {
        "httpGet": {
            "path": config["readiness_path"],
            "port": config["container_port"]
        },
        "initialDelaySeconds": 45,
        "periodSeconds": 10,
        "failureThreshold": 6
    }

    values["livenessProbe"] = {
        "httpGet": {
            "path": config["liveness_path"],
            "port": config["container_port"]
        },
        "initialDelaySeconds": 90,
        "periodSeconds": 15,
        "failureThreshold": 10
    }

    # Env
    if config["env"]:
        values["env"] = config["env"]
    else:
        values.pop("env", None)

    write_yaml(dev_file, values)
    print(f"  ✅ Fixed: {dev_file}")

def main():
    print("🚀 Fixing DEV Helm values...")
    for svc, cfg in SERVICES.items():
        fix_service(svc, cfg)
    print("\n🎉 Done. Review changes and commit.")

if __name__ == "__main__":
    main()
