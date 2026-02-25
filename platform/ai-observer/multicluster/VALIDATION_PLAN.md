# Validation Test Plan (Minikube First)

## 1) Start Minikube

```powershell
minikube start
kubectl config use-context minikube
```

## 2) Deploy central collector + observer agent

```powershell
kubectl apply -k platform/ai-observer/multicluster/k8s
kubectl -n dev get deploy,svc | findstr /I "observer-agent ai-observer-central-collector ai-observer-central-otel"
```

## 3) Push simulated telemetry

```powershell
kubectl -n dev port-forward svc/ai-observer-central-collector 8081:8081
python platform/ai-observer/multicluster/scripts/generate_telemetry.py --url http://127.0.0.1:8081/api/agent/push --cluster minikube-dev --count 10
```

## 4) Verify dashboards

- Start stack locally if needed:

```powershell
cd observability/multicluster-stack
docker compose up -d --build
```

- Open `http://127.0.0.1:3000` and confirm `Multi-Cluster Observer Overview` shows:
  - `Metric Samples Accepted`
  - `Log Records Accepted`
  - `Trace Records Accepted`
  - `Latest Agent Metric Values`

## 5) Validate auth and endpoint

```powershell
./platform/ai-observer/multicluster/scripts/test_agent_push.ps1 -CollectorUrl http://127.0.0.1:8081/api/agent/push -Token dev-agent-token -ClusterId minikube-dev
```

Expected results:
- `/api/agent/push` returns `accepted=true`.
- Missing/invalid token returns HTTP 401.
- `/api/observability/history?cluster=minikube-dev` only returns `cluster_id=minikube-dev`.
- `/api/observability/history` (without query param) still returns unfiltered data for backward compatibility.