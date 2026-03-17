[CmdletBinding()]
param([switch]$KeepCluster)

$ErrorActionPreference = 'Stop'

$repoRoot = 'D:\Projects\Services'
$kafkaDir = Join-Path $repoRoot 'kafka-platform'
$observerDir = Join-Path $repoRoot 'observer-stack\deploy\docker'

function Resolve-Tool {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)] [string]$Name,
    [string[]]$Fallbacks
  )
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
  throw "Missing required tool: $Name"
}

$docker = Resolve-Tool -Name 'docker' -Fallbacks @('C:\Program Files\Docker\Docker\resources\bin\docker.exe')
$k3d = Resolve-Tool -Name 'k3d' -Fallbacks @('C:\Users\hp\AppData\Local\Microsoft\WinGet\Packages\k3d.k3d_Microsoft.Winget.Source_8wekyb3d8bbwe\k3d.exe')
$kubectl = Resolve-Tool -Name 'kubectl' -Fallbacks @('C:\Program Files\Docker\Docker\resources\bin\kubectl.exe')

Write-Host 'Stopping Kafka compose stack.'
Set-Location $kafkaDir
& $docker compose -f (Join-Path $kafkaDir 'docker-compose.yml') -p 'kafka-platform' down -v --remove-orphans

Write-Host 'Stopping Observer stack compose.'
Set-Location $observerDir
& $docker compose -f (Join-Path $observerDir 'docker-compose.yaml') -p 'observer-stack' down -v --remove-orphans

if (-not $KeepCluster) {
  Write-Host 'Removing k3d cluster leninkart-dev.'
  & $k3d cluster delete leninkart-dev | Out-Null
}

Write-Host 'Removing local helper namespaces from previous runs.'
& $kubectl delete namespace argocd --ignore-not-found=$true | Out-Null
& $kubectl delete namespace dev --ignore-not-found=$true | Out-Null

if ($KeepCluster) {
  Write-Host 'Cluster kept; deleting only app/compose workloads.'
}

Write-Host 'Local environment teardown complete.'
