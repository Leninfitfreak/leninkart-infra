# Vault Quick Commands
# ====================

# Set Vault address (run in every new terminal)
$env:VAULT_ADDR='http://127.0.0.1:8200'

# Function to port-forward to Vault
function Start-VaultPortForward {
    Write-Host "Starting port-forward to Vault..."
    Start-Job -ScriptBlock {
        kubectl port-forward -n vault svc/vault 8200:8200
    }
    Start-Sleep -Seconds 3
}

# Function to initialize Vault
function Initialize-Vault {
    vault operator init -key-shares=1 -key-threshold=1 -format=json | Out-File vault-keys.json
    $keys = Get-Content vault-keys.json | ConvertFrom-Json
    
    Write-Host "=================================================="
    Write-Host "SAVE THESE CREDENTIALS SECURELY!"
    Write-Host "=================================================="
    Write-Host "Unseal Key: $($keys.unseal_keys_b64[0])"
    Write-Host "Root Token: $($keys.root_token)"
    Write-Host "=================================================="
    Write-Host ""
    Write-Host "Credentials saved to: vault-keys.json"
    Write-Host "Run: Unseal-Vault to unseal now"
}

# Function to unseal Vault
function Unseal-Vault {
    $keys = Get-Content vault-keys.json | ConvertFrom-Json
    vault operator unseal $keys.unseal_keys_b64[0]
}

# Function to login to Vault
function Login-Vault {
    $keys = Get-Content vault-keys.json | ConvertFrom-Json
    vault login $keys.root_token
}

# Function to check Vault status
function Get-VaultStatus {
    vault status
}

# Function to store a secret
function Set-VaultSecret {
    param(
        [string]$Path,
        [hashtable]$Data
    )
    
    $dataArgs = @()
    foreach ($key in $Data.Keys) {
        $dataArgs += "$key=$($Data[$key])"
    }
    
    vault kv put "secret/$Path" @dataArgs
}

# Function to get a secret
function Get-VaultSecret {
    param([string]$Path)
    vault kv get "secret/$Path"
}

# Function to list secrets
function Get-VaultSecrets {
    param([string]$Path = "leninkart")
    vault kv list "secret/$Path"
}

# Example usage:
# Start-VaultPortForward
# Initialize-Vault
# Unseal-Vault
# Login-Vault
# Set-VaultSecret -Path "leninkart/test" -Data @{username="user"; password="pass"}
# Get-VaultSecret -Path "leninkart/test"
