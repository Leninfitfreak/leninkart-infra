[CmdletBinding()]
param(
    [string]$IngressUrl = 'http://127.0.0.1',
    [switch]$RunValidationEngine = $false
)

$ErrorActionPreference = 'Stop'

$repoRoot = 'D:\Projects\Services'
$infraRoot = 'D:\Projects\Services\leninkart-infra'
$validationRoot = 'D:\Projects\Services\project-validation'
$reportPath = Join-Path $infraRoot 'local-deployment-report.json'
$checks = [System.Collections.Generic.List[object]]::new()

function Resolve-Tool {
  [CmdletBinding()]
  param([Parameter(Mandatory)] [string]$Name, [string[]]$Fallbacks)
  $command = Get-Command $Name -ErrorAction SilentlyContinue
  if ($command) { return $command.Source }
  foreach ($candidate in $Fallbacks) {
    if (Test-Path $candidate) {
      if ((Get-Item $candidate).PSIsContainer) {
        $exe = Join-Path $candidate "$Name.exe"
        if (Test-Path $exe) { return $exe }
      }
      else { return $candidate }
    }
  }
  return $null
}

function Add-Check([string]$name, [bool]$ok, [string]$details) {
  $script:checks.Add([PSCustomObject]@{ name = $name; ok = $ok; details = $details; checked_at = (Get-Date).ToString('s') })
}

function Require([string]$toolName, [string[]]$fallbacks) {
  $path = Resolve-Tool -Name $toolName -Fallbacks $fallbacks
  if (-not $path) { Add-Check $toolName $false "not found"; throw "Missing required tool: $toolName" }
  Add-Check $toolName $true $path
  return $path
}

function Http-Check([string]$name, [string]$url, [string]$method = 'GET', [string]$body = '') {
  try {
    if ($body) {
      $null = Invoke-WebRequest -Uri $url -Method $method -UseBasicParsing -ContentType 'application/json' -Body $body -TimeoutSec 20
    return 200
  }
  else {
    $resp = Invoke-WebRequest -Uri $url -Method $method -UseBasicParsing -TimeoutSec 20
    return $resp.StatusCode
  }
  }
  catch {
    return 0
  }
}

$docker = Require 'docker' @('C:\Program Files\Docker\Docker\resources\bin\docker.exe')
$kubectl = Require 'kubectl' @('C:\Program Files\Docker\Docker\resources\bin\kubectl.exe')
$k3d = Require 'k3d' @('C:\Users\hp\AppData\Local\Microsoft\WinGet\Packages\k3d.k3d_Microsoft.Winget.Source_8wekyb3d8bbwe\k3d.exe')

try {
  & $docker info >$null
  Add-Check 'docker-daemon' ($LASTEXITCODE -eq 0) 'Docker daemon available.'
} catch { Add-Check 'docker-daemon' $false $_.Exception.Message }

try {
  $clusters = & $k3d cluster list
  $clustersText = $clusters | Out-String
  $hasCluster = [bool]($clustersText -match 'leninkart-dev')
  Add-Check 'k3d-cluster' $hasCluster "k3d cluster leninkart-dev present: $hasCluster"
} catch { Add-Check 'k3d-cluster' $false $_.Exception.Message }

try {
  $nodes = & $kubectl get nodes --no-headers
  Add-Check 'k8s-nodes' (-not [string]::IsNullOrWhiteSpace($nodes)) "nodes output captured"
} catch {
  Add-Check 'k8s-nodes' $false $_.Exception.Message
}

try {
  $pods = & $kubectl get pods -n dev --no-headers
  $hasFrontend = ($pods | Where-Object { $_ -match 'frontend' -and $_ -match '1/1' }).Count -gt 0
  $hasProduct = ($pods | Where-Object { $_ -match 'product-service|product' -and $_ -match '1/1' }).Count -gt 0
  $hasOrder = ($pods | Where-Object { $_ -match 'order-service|order' -and $_ -match '1/1' }).Count -gt 0
  Add-Check 'k8s-pods-dev' ($hasFrontend -and $hasProduct -and $hasOrder) "frontend=$hasFrontend product=$hasProduct order=$hasOrder"
} catch {
  Add-Check 'k8s-pods-dev' $false $_.Exception.Message
}

try {
  $argocdHealth = & $kubectl get application leninkart-root -n argocd -o jsonpath='{.status.health.status}' --ignore-not-found
  Add-Check 'argocd-root' (-not [string]::IsNullOrWhiteSpace($argocdHealth)) "leninkart-root health=$argocdHealth"
} catch {
  Add-Check 'argocd-root' $false $_.Exception.Message
}

try {
  $kafkaTopicsRaw = & $docker exec kafka-platform sh -c "kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null"
  $kafkaTopics = $kafkaTopicsRaw -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }
  $requiredTopics = @('product-orders', 'product-events', 'order-events', 'order-created')
  $hasRequiredTopics = $requiredTopics | Where-Object { $_ -in $kafkaTopics }
  Add-Check 'kafka-topics' ($hasRequiredTopics.Count -eq $requiredTopics.Count) "topics: $($kafkaTopics.Count), required missing: $(($requiredTopics | Where-Object { $_ -notin $kafkaTopics }) -join ', ')"
} catch {
  Add-Check 'kafka-topics' $false $_.Exception.Message
}

$ingress = $IngressUrl.TrimEnd('/')
try {
  $frontendCode = Http-Check 'frontend' "$ingress/"
  Add-Check 'frontend-ui' ($frontendCode -eq 200) "HTTP $frontendCode"
} catch {
  Add-Check 'frontend-ui' $false $_.Exception.Message
}

try {
  $obsCode = Http-Check 'observer-stack-ui' 'http://127.0.0.1:8080/'
  Add-Check 'observer-ui' ($obsCode -eq 200) "HTTP $obsCode"
} catch {
  Add-Check 'observer-ui' $false $_.Exception.Message
}

$orderFlowOk = $false
$orderFlowDetails = ''
try {
  $rand = Get-Random -Maximum 1000000
  $email = "validator-$rand@example.com"
  $password = 'Validator@123'

  $signup = Invoke-RestMethod -Uri "$ingress/auth/signup" -Method POST -ContentType 'application/json' -Body (@{ fullName='Verifier'; email=$email; password=$password } | ConvertTo-Json) -TimeoutSec 30
  if (-not $signup.token) {
    throw 'signup response missing token'
  }

  $login = Invoke-RestMethod -Uri "$ingress/auth/login" -Method POST -ContentType 'application/json' -Body (@{ email=$email; password=$password } | ConvertTo-Json) -TimeoutSec 30
  if (-not $login.token) { throw 'login response missing token' }

  $headers = @{ Authorization = "Bearer $($login.token)" }
  $product = Invoke-RestMethod -Uri "$ingress/api/products" -Method POST -ContentType 'application/json' -Headers $headers -Body (@{ name='Verifier Product'; price=199; description='validation' } | ConvertTo-Json) -TimeoutSec 30
  if (-not $product.id) { throw 'product create response missing id' }

  $order = Invoke-RestMethod -Uri "$ingress/api/products/$($product.id)/order" -Method POST -Headers $headers -TimeoutSec 20
  $orders = $null
  for ($attempt = 0; $attempt -lt 6; $attempt++) {
    Start-Sleep -Seconds 2
    $orders = Invoke-RestMethod -Uri "$ingress/api/orders" -Method GET -Headers $headers -TimeoutSec 30
    if ($orders -and $orders.Count -gt 0) { break }
  }
  if (-not $orders) { throw 'orders list returned empty' }

  $orderFlowOk = $true
  $orderFlowDetails = 'Signup, login, create product, create order, get orders succeeded.'
  if ($orders.Count -gt 0) { $orderFlowDetails += " orders=$($orders.Count)." } else { $orderFlowDetails += ' orders empty.'; $orderFlowOk = $false }
} catch {
  $orderFlowDetails = $_.Exception.Message
}
Add-Check 'sample-order-flow' $orderFlowOk $orderFlowDetails

if ($RunValidationEngine) {
  $py = Resolve-Tool -Name 'python' -Fallbacks @('python')
  if ($py) {
    try {
      Set-Location $validationRoot
      & $py .\run_validation.py
      Add-Check 'project-validation' ($LASTEXITCODE -eq 0) "ExitCode: $LASTEXITCODE"
    }
    catch {
      Add-Check 'project-validation' $false $_.Exception.Message
    }
  }
  else {
    Add-Check 'project-validation' $false 'python not found'
  }
}

$allOk = -not ($checks | Where-Object { -not $_.ok })
$report = @{
  generated_at = (Get-Date).ToString('o')
  ingress_url = $IngressUrl
  all_checks_passed = $allOk
  checks = $checks
}
$report | ConvertTo-Json -Depth 6 | Set-Content -Path $reportPath -Encoding utf8
Write-Host "Verification report saved to $reportPath"

if (-not $allOk) {
  Write-Host 'Local verification found failures. See report for details.'
  exit 1
}

Write-Host 'Local verification passed.'
exit 0
