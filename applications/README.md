# Applications

All microservices and application-level components.

## Structure
- Each service has its own directory
- Helm charts in `<service>/helm/`
- Additional manifests in `<service>/manifests/` (if needed)

## Services
- **frontend**: React-based user interface
- **product-service**: Product catalog management
- **order-service**: Order processing
- **ingress**: Ingress controller configuration
