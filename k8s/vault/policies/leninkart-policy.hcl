# LeninKart Application Policy
path "secret/data/leninkart/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/leninkart/*" {
  capabilities = ["read", "list"]
}

path "database/creds/leninkart-*" {
  capabilities = ["read"]
}
