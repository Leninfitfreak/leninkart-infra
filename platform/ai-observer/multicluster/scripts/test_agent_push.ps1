param(
  [string]$CollectorUrl = "http://127.0.0.1:8081/api/agent/push",
  [string]$Token = "dev-agent-token",
  [string]$ClusterId = "minikube-dev"
)

$payload = @{
  cluster_id = $ClusterId
  metrics = @(
    @{ name = "manual_qps"; value = 42.5; labels = @{ service = "curl-test" } }
  )
  logs = @(
    @{ message = "manual log"; severity = "info"; service = "curl-test" }
  )
  traces = @(
    @{ operation = "manual.trace"; duration_ms = 22; service = "curl-test"; status = "ok" }
  )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Method Post -Uri $CollectorUrl -Headers @{
  "Content-Type" = "application/json"
  "X-Agent-Token" = $Token
} -Body $payload

Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8081/api/observability/history?cluster=$ClusterId"
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8081/api/observability/dashboard?cluster=$ClusterId"