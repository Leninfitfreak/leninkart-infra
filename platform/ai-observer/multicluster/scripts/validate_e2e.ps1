param(
  [string]$RepoRoot = "C:\Projects\infra\leninkart-infra"
)

Write-Host "[1/4] Validate kustomize"
kubectl kustomize "$RepoRoot/platform/ai-observer/multicluster" | Out-Null

Write-Host "[2/4] Validate docker compose"
Push-Location "$RepoRoot/observability/multicluster-stack"
docker compose config | Out-Null
Pop-Location

Write-Host "[3/4] Run collector API tests"
Push-Location "$RepoRoot/platform/ai-observer/multicluster"
python -m pip install -r central-collector/requirements.txt -q
python -m pip install pytest -q
python -m pytest -q tests
Pop-Location

Write-Host "[4/4] Smoke push endpoint via generated payload (collector must be reachable)"
python "$RepoRoot/platform/ai-observer/multicluster/scripts/generate_telemetry.py" --count 1

Write-Host "Validation completed"