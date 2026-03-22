# Observability

GitOps-managed observability for LeninKart using Prometheus, Grafana, Loki, and Promtail.

## Components
- **prometheus**: scrape-based metrics collection for product-service, order-service, and Kafka
- **grafana**: dashboards, login, and operator-facing visualization
- **loki**: lightweight log storage for Kubernetes application logs
- **promtail**: Kubernetes log shipping into Loki

## Architecture
```
Kubernetes services -> Prometheus -> Grafana
Kubernetes pod logs -> Promtail -> Loki -> Grafana
Kafka JMX exporter -> Prometheus -> Grafana
```
