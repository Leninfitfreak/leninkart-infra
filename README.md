# LeninKart Infrastructure

Production-grade Kubernetes infrastructure for the LeninKart e-commerce platform.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    GitOps (ArgoCD)                      │
│  Declarative infrastructure management across envs      │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼────────┐ ┌──────▼──────┐ ┌───────▼────────┐
│ Applications   │ │  Platform   │ │ Observability  │
├────────────────┤ ├─────────────┤ ├────────────────┤
│ • Frontend     │ │ • Kafka     │ │ • Prometheus   │
│ • Product API  │ │ • PostgreSQL│ │ • Grafana      │
│ • Order API    │ │ • Istio     │ │ • Jaeger       │
│ • Ingress      │ │ • Vault     │ │ • OTel         │
└────────────────┘ └─────────────┘ └────────────────┘
```

## 📁 Directory Structure

```
leninkart-infra/
├── applications/          # Microservices & application components
│   ├── frontend/         # React UI
│   ├── product-service/  # Product catalog API
│   ├── order-service/    # Order processing API
│   └── ingress/          # Ingress controller
│
├── platform/             # Infrastructure components
│   ├── kafka/           # Event streaming
│   ├── postgres/        # Database
│   ├── istio/           # Service mesh
│   ├── vault/           # Secrets management
│   └── external-secrets/# ESO integration
│
├── observability/        # Monitoring & tracing
│   ├── prometheus/      # Metrics collection
│   ├── grafana/         # Dashboards
│   ├── jaeger/          # Distributed tracing
│   └── otel/            # OpenTelemetry collector
│
├── argocd/              # GitOps configurations
│   ├── applications/    # App-of-apps pattern
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   └── projects/        # ArgoCD projects
│
├── docs/                # Documentation
└── scripts/             # Utility scripts
```

## 🚀 Quick Start

### Prerequisites
- Kubernetes cluster (Minikube/Kind for local)
- kubectl configured
- ArgoCD installed

### Deploy Everything

```bash
# Apply ArgoCD root application
kubectl apply -f argocd/leninkart-root.yaml

# Watch deployment
kubectl get applications -n argocd -w
```

### Access Services

```bash
# Frontend
kubectl port-forward -n dev svc/leninkart-frontend 8080:80

# Product API
kubectl port-forward -n dev svc/leninkart-product-service 8081:8081

# Order API
kubectl port-forward -n dev svc/leninkart-order-service 8082:8080

# Grafana
kubectl port-forward -n dev svc/grafana 3000:3000

# Jaeger UI
kubectl port-forward -n dev svc/jaeger-query 16686:16686
```

## 🔧 Tech Stack

| Component | Technology |
|-----------|------------|
| **Container Orchestration** | Kubernetes |
| **GitOps** | ArgoCD |
| **Service Mesh** | Istio |
| **Secrets Management** | HashiCorp Vault + External Secrets Operator |
| **Message Broker** | Apache Kafka (KRaft mode) |
| **Database** | PostgreSQL |
| **Metrics** | Prometheus |
| **Tracing** | Jaeger + OpenTelemetry |
| **Visualization** | Grafana |
| **Ingress** | NGINX Ingress Controller |

## 📊 Observability

### Metrics
- **Prometheus** scrapes metrics from all services
- **Grafana** provides dashboards for visualization
- Custom dashboards for each microservice

### Tracing
- **OpenTelemetry** instrumentation in Java/Spring Boot services
- **Istio** generates service mesh traces
- **Jaeger** stores and visualizes distributed traces

### Architecture
```
Services → OTel Agent → OTel Collector → Jaeger (traces)
                                      ↓
                               Prometheus (metrics)
                                      ↓
                              Grafana (dashboards)
```

## 🔐 Secrets Management

All secrets are managed by HashiCorp Vault and synced to Kubernetes via External Secrets Operator.

```yaml
# Example: Database credentials
ExternalSecret → Vault → Kubernetes Secret → Pod
```

No secrets are stored in Git!

## 🌐 Networking

**Istio Service Mesh** handles all traffic:
- mTLS between services
- Circuit breaking & retries
- Traffic splitting (A/B testing)
- Observability (automatic tracing)

**Ingress Gateway** routes external traffic:
- `/` → Frontend
- `/api/products` → Product Service
- `/api/orders` → Order Service

## 🏷️ Environments

| Environment | Namespace | Branch | Auto-Deploy |
|-------------|-----------|--------|-------------|
| Development | `dev` | `dev` | ✅ Yes |
| Staging | `staging` | `staging` | ✅ Yes |
| Production | `prod` | `main` | ❌ Manual |

## 📚 Documentation

- [Vault Setup](docs/VAULT_SETUP.md)
- [Observability Guide](docs/OBSERVABILITY.md)
- [Istio Configuration](docs/ISTIO.md)

## 🤝 Contributing

1. Make changes in feature branch
2. Update relevant environment (dev/staging/prod)
3. Commit and push
4. ArgoCD auto-syncs changes
5. Verify deployment

## 📄 License

Private - LeninKart Internal Use Only
