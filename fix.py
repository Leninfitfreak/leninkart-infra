import yaml
from pathlib import Path

INGRESS_FILE = Path("helm/ingress/templates/ingress.yaml")

def main():
    ingress = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {
            "name": "leninkart-ingress"
        },
        "spec": {
            "ingressClassName": "nginx",
            "rules": [
                {
                    "http": {
                        "paths": [
                            {
                                "path": "/api/products",
                                "pathType": "Prefix",
                                "backend": {
                                    "service": {
                                        "name": "product-service",
                                        "port": {"number": 8080}
                                    }
                                }
                            },
                            {
                                "path": "/api/orders",
                                "pathType": "Prefix",
                                "backend": {
                                    "service": {
                                        "name": "order-service",
                                        "port": {"number": 8080}
                                    }
                                }
                            },
                            {
                                "path": "/",
                                "pathType": "Prefix",
                                "backend": {
                                    "service": {
                                        "name": "frontend",
                                        "port": {"number": 80}
                                    }
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }

    INGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INGRESS_FILE, "w") as f:
        yaml.safe_dump(ingress, f, sort_keys=False)

    print("✅ Ingress fixed (Prefix-safe, ArgoCD-safe)")

if __name__ == "__main__":
    main()