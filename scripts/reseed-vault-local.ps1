[CmdletBinding()]
param(
    [string]$WorkspaceRoot = 'D:\Projects\Services',
    [string]$Namespace = 'vault',
    [string]$AppNamespace = 'dev',
    [string]$SignozApiKey
)

$ErrorActionPreference = 'Stop'

function Get-EnvValue {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Name
    )

    $line = Get-Content -Path $Path | Where-Object { $_ -match "^\s*$([regex]::Escape($Name))\s*[:=]" } | Select-Object -First 1
    if (-not $line) {
        return $null
    }

    return ($line -split '[:=]', 2)[1].Trim()
}

function Get-SecretValue {
    param(
        [Parameter(Mandatory)] [string]$Secret,
        [Parameter(Mandatory)] [string]$Key
    )

    $encoded = kubectl get secret $Secret -n $AppNamespace -o "jsonpath={.data.$Key}"
    if (-not $encoded) {
        return $null
    }

    return [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($encoded))
}

function Invoke-VaultWrite {
    param(
        [Parameter(Mandatory)] [string]$Command,
        [Parameter(Mandatory)] [string]$RootToken
    )

    $script = @'
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN='__ROOT_TOKEN__'
__COMMAND__
'@

    $script = $script.Replace('__ROOT_TOKEN__', $RootToken).Replace('__COMMAND__', $Command)
    kubectl exec -n $Namespace vault-0 -- sh -lc $script
}

function Get-VaultValue {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Property,
        [Parameter(Mandatory)] [string]$RootToken
    )

    $script = @'
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN='__ROOT_TOKEN__'
vault kv get -field=__PROPERTY__ __PATH__ 2>/dev/null || true
'@

    $script = $script.Replace('__ROOT_TOKEN__', $RootToken).Replace('__PROPERTY__', $Property).Replace('__PATH__', $Path)
    return (kubectl exec -n $Namespace vault-0 -- sh -lc $script | Out-String).Trim()
}

$rootEnv = Join-Path $WorkspaceRoot '.env'
$envSignozApiKey = Get-EnvValue -Path $rootEnv -Name 'signoz_api_key'

$postgresDb = Get-SecretValue -Secret 'postgres-secret' -Key 'POSTGRES_DB'
$postgresUser = Get-SecretValue -Secret 'postgres-secret' -Key 'POSTGRES_USER'
$postgresPassword = Get-SecretValue -Secret 'postgres-secret' -Key 'POSTGRES_PASSWORD'

if ([string]::IsNullOrWhiteSpace($postgresDb) -or [string]::IsNullOrWhiteSpace($postgresUser) -or [string]::IsNullOrWhiteSpace($postgresPassword)) {
    throw 'Could not read the current postgres admin credentials from the live cluster.'
}

$productValues = Join-Path $WorkspaceRoot 'leninkart-infra\applications\product-service\helm\values-dev.yaml'
$orderValues = Join-Path $WorkspaceRoot 'leninkart-infra\applications\order-service\helm\values-dev.yaml'
$bootstrapJson = kubectl exec -n $Namespace vault-0 -- cat /vault/data/bootstrap-keys.json
$bootstrapJson = ($bootstrapJson | Out-String) -replace '\s', ''
$rootToken = [regex]::Match($bootstrapJson, '"root_token":"([^"]+)"').Groups[1].Value

if ([string]::IsNullOrWhiteSpace($rootToken)) {
    throw 'Could not read the Vault root token from the bootstrap file.'
}

if ([string]::IsNullOrWhiteSpace($SignozApiKey)) {
    $SignozApiKey = $envSignozApiKey
}

if ([string]::IsNullOrWhiteSpace($SignozApiKey)) {
    $SignozApiKey = Get-VaultValue -Path 'secret/leninkart/observability' -Property 'signoz_api_key' -RootToken $rootToken
}

$productJwt = (Get-Content $productValues | Select-String 'APP_JWT_SECRET:\s*"?([^"\r\n]+)' | Select-Object -First 1).Matches.Groups[1].Value
$productBootstrap = (Get-Content $productValues | Select-String 'KAFKA_BOOTSTRAP_SERVERS:\s*([^"\r\n]+)' | Select-Object -First 1).Matches.Groups[1].Value.Trim('"')
$jwtIssuer = (Get-Content $productValues | Select-String 'APP_JWT_ISSUER:\s*"?([^"\r\n]+)' | Select-Object -First 1).Matches.Groups[1].Value
$jwtTtl = (Get-Content $productValues | Select-String 'APP_JWT_TTL_SECONDS:\s*"?([^"\r\n]+)' | Select-Object -First 1).Matches.Groups[1].Value

if ([string]::IsNullOrWhiteSpace($productJwt) -or [string]::IsNullOrWhiteSpace($productBootstrap)) {
    throw 'Could not infer the current product-service JWT/Kafka values from values-dev.yaml.'
}

Invoke-VaultWrite -RootToken $rootToken -Command "vault kv put secret/leninkart/postgres/admin POSTGRES_DB='$postgresDb' POSTGRES_USER='$postgresUser' POSTGRES_PASSWORD='$postgresPassword'"
Invoke-VaultWrite -RootToken $rootToken -Command "vault kv put secret/leninkart/product-service/database username='$postgresUser' password='$postgresPassword'"
Invoke-VaultWrite -RootToken $rootToken -Command "vault kv put secret/leninkart/order-service/database username='$postgresUser' password='$postgresPassword'"
Invoke-VaultWrite -RootToken $rootToken -Command "vault kv put secret/leninkart/product-service/config jwt_secret='$productJwt' jwt_issuer='$jwtIssuer' jwt_ttl_seconds='$jwtTtl' api_key='local-dev'"
Invoke-VaultWrite -RootToken $rootToken -Command "vault kv put secret/leninkart/order-service/config jwt_secret='$productJwt' jwt_issuer='$jwtIssuer' jwt_ttl_seconds='$jwtTtl' api_key='local-dev'"
Invoke-VaultWrite -RootToken $rootToken -Command "vault kv put secret/leninkart/kafka/credentials bootstrap_servers='$productBootstrap'"
if (-not [string]::IsNullOrWhiteSpace($SignozApiKey)) {
    Invoke-VaultWrite -RootToken $rootToken -Command "vault kv put secret/leninkart/observability signoz_api_key='$SignozApiKey'"
}
Invoke-VaultWrite -RootToken $rootToken -Command "vault kv put secret/leninkart/auth jwt_secret='$productJwt' jwt_issuer='$jwtIssuer' jwt_ttl_seconds='$jwtTtl'"

Write-Host 'Vault local reseed complete.'
