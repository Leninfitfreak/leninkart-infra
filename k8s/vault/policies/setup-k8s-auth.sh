#!/bin/bash
# Script to configure Vault Kubernetes authentication

export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="<ROOT_TOKEN>"  # Replace with actual root token

# Create policy
vault policy write leninkart-policy /vault/policies/leninkart-policy.hcl

# Create Kubernetes role
vault write auth/kubernetes/role/leninkart-role \
  bound_service_account_names=vault-auth \
  bound_service_account_namespaces=dev \
  policies=leninkart-policy \
  ttl=24h
  
# Enable database secrets engine
vault secrets enable database

# Configure PostgreSQL dynamic secrets
vault write database/config/leninkart-postgres \
  plugin_name=postgresql-database-plugin \
  allowed_roles="leninkart-*" \
  connection_url="postgresql://{{username}}:{{password}}@postgres.dev.svc.cluster.local:5432/leninkart?sslmode=disable" \
  username="postgres" \
  password="postgres"

# Create database role for product-service
vault write database/roles/leninkart-product \
  db_name=leninkart-postgres \
  creation_statements="CREATE ROLE \"{{name}\}" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\"; \
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO \"{{name}\}";" \
  default_ttl="1h" \
  max_ttl="24h"

# Create database role for order-service
vault write database/roles/leninkart-order \
  db_name=leninkart-postgres \
  creation_statements="CREATE ROLE \"{{name}\}" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\"; \
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO \"{{name}\}";" \
  default_ttl="1h" \
  max_ttl="24h"

echo "Vault configuration complete!"
