[CmdletBinding()]
param(
    [string]$WorkspaceRoot = 'D:\Projects\Services',
    [switch]$RecreateCluster = $false,
    [string]$ContextName = 'k3d-leninkart-dev'
)

$ErrorActionPreference = 'Stop'

$repoRoot = $WorkspaceRoot
$kafkaDir = Join-Path $repoRoot 'kafka-platform'
$observerDir = Join-Path $repoRoot 'observer-stack\deploy\docker'
$infraDir = Join-Path $repoRoot 'leninkart-infra'
$clusterName = 'leninkart-dev'
$expectedContext = $ContextName

function Resolve-Tool {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)] [string]$Name,
    [string[]]$Fallbacks
  )
  $command = Get-Command $Name -ErrorAction SilentlyContinue
  if ($command) {
    return $command.Source
  }
  foreach ($candidate in $Fallbacks) {
    if ([string]::IsNullOrWhiteSpace($candidate)) {
      continue
    }
    if ($candidate -like '*\*' -and (Test-Path (Split-Path $candidate))) {
      $parent = Split-Path $candidate
      $leaf = Split-Path $candidate -Leaf
      $found = Get-ChildItem -Path $parent -Recurse -Filter $leaf -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
      if ($found) {
        return $found
      }
      continue
    }
    if ($candidate -like '*' -and (Test-Path $candidate)) {
      if ((Get-Item $candidate).PSIsContainer) {
        $candidateExe = Join-Path $candidate "$Name.exe"
        if (Test-Path $candidateExe) {
          return $candidateExe
        }
      }
      else {
        return $candidate
      }
    }
  }
  throw "Required tool '$Name' was not found in PATH or fallback paths."
}

function Ensure-DockerRunning {
  param([int]$TimeoutSeconds = 180)
  $dockerBinary = Resolve-Tool -Name 'docker' -Fallbacks @('C:\Program Files\Docker\Docker\resources\bin\docker.exe')
  $desktopPath = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'

  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
    try {
      & $dockerBinary info --format '{{json .}}' 2>$null | Out-Null
      $exitCode = $LASTEXITCODE
    }
    catch {
      $exitCode = 1
    }
    if ($exitCode -eq 0) {
      return
    }
    if (-not (Get-Process 'Docker Desktop' -ErrorAction SilentlyContinue) -and (Test-Path $desktopPath)) {
      Start-Process -FilePath $desktopPath | Out-Null
    }
    Start-Sleep -Seconds 3
  }

  throw 'Docker Desktop is not running or Docker daemon is unavailable after waiting.'
}

function Ensure-K3dCluster {
  $k3d = Resolve-Tool -Name 'k3d' -Fallbacks @('C:\Users\hp\AppData\Local\Microsoft\WinGet\Packages\k3d.k3d_Microsoft.Winget.Source_8wekyb3d8bbwe\k3d.exe')
  $clusterJson = & $k3d cluster list --output json | ConvertFrom-Json
  $existing = $clusterJson | Where-Object { $_.name -eq $clusterName }

  if ($RecreateCluster -and $existing) {
    Write-Host "Recreate requested. Deleting existing cluster $clusterName."
    & $k3d cluster delete $clusterName | Out-Null
    $existing = $null
  }

  if (-not $existing) {
    Write-Host "Creating k3d cluster $clusterName."
    & $k3d cluster create $clusterName `
      --servers 1 --agents 0 `
      --api-port 127.0.0.1:6550 `
      --k3s-arg '--disable=traefik@server:*' `
      --port '80:80@loadbalancer' `
      --port '443:443@loadbalancer' `
      --wait
  }
  else {
    Write-Host "Reusing cluster $clusterName."
  }
}

function Ensure-ExternalConnectivity {
  $expectedLabel = 'com.docker.compose.network'
  $existing = & $docker network ls --format '{{.Name}}' 2>$null | Select-String '^signoz-net$'
  $needsCreate = $false

  if (-not $existing) {
    $needsCreate = $true
  }
  else {
    try {
      $inspect = & $docker network inspect signoz-net --format '{{json .}}' 2>$null | ConvertFrom-Json
      $labelValue = $inspect.ConfigOnly + '' # keep JSON shape simple if parse edge case
      if ($inspect.Labels) {
        $labelValue = $inspect.Labels."$expectedLabel"
      }
      if ($labelValue -ne 'signoz-net') {
        $needsCreate = $true
        Write-Host "Existing signoz-net does not match compose labels. Recreating."
      }
    }
    catch {
      $needsCreate = $true
    }
  }

  if ($needsCreate) {
    if ($existing) {
      & $docker network rm signoz-net >$null 2>&1
    }
    & $docker network create signoz-net `
      --driver bridge `
      --label 'com.docker.compose.network=signoz-net' `
      --label 'com.docker.compose.project=observer-stack' `
      --label 'com.docker.compose.version=2.34.0' >$null 2>&1
  }
}

function Wait-ForKafka {
  $maxAttempts = 60
  for ($i = 0; $i -lt $maxAttempts; $i++) {
    & $docker exec kafka-platform sh -c 'kafka-topics --bootstrap-server localhost:9092 --list >/dev/null 2>&1'
    if ($LASTEXITCODE -eq 0) {
      return
    }
    Start-Sleep -Seconds 2
  }
  throw 'Kafka did not become ready in time.'
}

function Ensure-ArgoCD {
  $manifest = 'https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml'
  if (-not (& $kubectl get ns argocd -o name --ignore-not-found)) {
    & $kubectl create namespace argocd | Out-Null
  }
  if (-not (& $kubectl get deployment -n argocd argocd-server -o name --ignore-not-found)) {
    Write-Host 'Installing ArgoCD manifests.'
    & $kubectl apply -n argocd -f $manifest
  }
  & $kubectl rollout status deployment -n argocd argocd-server --timeout=240s | Out-Null
}

function Ensure-IngressController {
  param([string]$Helm)
  $existing = & $kubectl get deployment -n ingress-nginx ingress-nginx-controller -o name --ignore-not-found 2>$null
  if ($existing) {
    return
  }
  Write-Host 'Installing ingress-nginx controller.'
  if ($Helm) {
    try {
      & $helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx | Out-Null
      & $helm repo update | Out-Null
      & $helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx `
        --namespace ingress-nginx --create-namespace `
        --set controller.service.type=LoadBalancer `
        --set controller.admissionWebhooks.enabled=false | Out-Null
      return
    }
    catch {
      Write-Host 'Helm install for ingress-nginx failed; falling back to static manifest.'
    }
  }
  & $kubectl apply -f 'https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller/v1.12.3/deploy/static/provider/cloud/deploy.yaml'
}

function Wait-Service {
  param([string]$Namespace, [string]$Label)
  & $kubectl wait --for=condition=Ready pod -n $Namespace -l $Label --timeout=180s | Out-Null
}

$docker = Resolve-Tool -Name 'docker' -Fallbacks @('C:\Program Files\Docker\Docker\resources\bin\docker.exe')
$kubectl = Resolve-Tool -Name 'kubectl' -Fallbacks @('C:\Program Files\Docker\Docker\resources\bin\kubectl.exe', 'C:\Program Files\Docker\Docker\resources\bin\kubectl.exe')
$helm = Resolve-Tool -Name 'helm' -Fallbacks @('C:\Users\hp\AppData\Local\Microsoft\WinGet\Packages\Helm.Helm_Microsoft.Winget.Source_8wekyb3d8bbwe\windows-amd64\helm.exe')

Write-Host '1/7) Checking Docker daemon'
Ensure-DockerRunning

Write-Host '2/7) Ensuring k3d cluster exists'
Ensure-K3dCluster

Write-Host '3/7) Applying kubectl context'
& $kubectl config use-context $expectedContext | Out-Null

Write-Host '4/7) Ensuring support networks'
Ensure-ExternalConnectivity

Write-Host '5/7) Starting Kafka compose'
Set-Location $kafkaDir
& $docker compose -f (Join-Path $kafkaDir 'docker-compose.yml') -p 'kafka-platform' up -d
Wait-ForKafka

Write-Host '6/7) Creating Kafka topics'
& $docker exec kafka-platform sh -c 'sh /usr/local/bin/create-topics.sh'

Write-Host '7/7) Starting Observer stack compose'
Set-Location $observerDir
& $docker compose -f (Join-Path $observerDir 'docker-compose.yaml') -p 'observer-stack' up -d

Write-Host 'Installing ArgoCD and syncing GitOps root.'
Ensure-ArgoCD
& $kubectl create namespace dev --dry-run=client -o yaml | & $kubectl apply -f -
& $kubectl apply -n argocd -f (Join-Path $infraDir 'argocd\leninkart-root.yaml')

Ensure-IngressController -Helm $helm
& $kubectl wait --namespace ingress-nginx --for=condition=available deploy/ingress-nginx-controller --timeout=240s | Out-Null

Write-Host 'Waiting for application pods.'
Wait-Service -Namespace 'argocd' -Label 'app.kubernetes.io/name=argocd-server'
Wait-Service -Namespace 'dev' -Label 'app=frontend'
Wait-Service -Namespace 'dev' -Label 'app=product-service'
Wait-Service -Namespace 'dev' -Label 'app.kubernetes.io/name=order-service'

Write-Host 'Deployment bootstrap complete.'
Write-Host "Frontend: http://127.0.0.1/"
Write-Host "ArgoCD: kubectl port-forward -n argocd svc/argocd-server 8085:443"
Write-Host "Observer stack: http://127.0.0.1:8080"
Write-Host "Deep Observer: http://127.0.0.1:3000"
Write-Host "Deep Observer API health: http://127.0.0.1:8081/health"
