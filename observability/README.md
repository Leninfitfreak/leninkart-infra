# Observability

Monitoring, metrics, and distributed tracing.

## Components
- **prometheus**: Metrics collection and storage
- **grafana**: Metrics visualization and dashboards
- **jaeger**: Distributed tracing
- **otel**: OpenTelemetry collector for trace/metric collection
- **multicluster-stack**: Additive Docker Compose stack for Mimir/Loki/Tempo + central collector integration

## Architecture
```
Services → OTel Collector → Prometheus (metrics)
                          ↓
                        Jaeger (traces)
                          ↓
                    Grafana (visualization)
```
