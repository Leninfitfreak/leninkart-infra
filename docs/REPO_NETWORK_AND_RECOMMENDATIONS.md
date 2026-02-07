# LeninKart Infra — Repo Analysis & Network Access Guide

This document summarizes the repository structure, how traffic flows through the network layer (Istio), how to access applications in the cluster, findings from a quick repo walk, and prioritized recommendations you can act on immediately.

Location
- File created: `docs/REPO_NETWORK_AND_RECOMMENDATIONS.md`

Summary
- Cluster network layer: Istio IngressGateway -> Gateway resource -> VirtualService -> Kubernetes Service -> Pod
- Repo stores Helm charts for applications under `applications/`, environment ArgoCD manifests under `argocd/`, platform services under `platform/`, and observability under `observability/`.
- The dev cluster observed in this session appears to be local (Minikube). The `istio-ingressgateway` service is a LoadBalancer with LoadBalancer Ingress `127.0.0.1` (tunneled locally) and NodePorts available.

What I examined
- Searched and removed ephemeral backup files (`_cleanup_backup/` and `_ingress_backup/`) and updated `.gitignore` (local commit created). 
- Inspected `istio-ingressgateway` service and ingress gateway pod(s). Found a Gateway named `leninkart-gateway` in `dev` namespace.

Repository map (where to find things)
- applications/
  - frontend/helm
  - order-service/helm
  - product-service/helm
  (Chart templates, values-dev.yaml and values.yaml live here)
- argocd/
  - applications/dev/ (per-environment ArgoCD app manifests)
- platform/
  - external-secrets/ (external-secrets config)
  - kafka/, postgres/, vault/ (platform k8s resources)
- observability/ (Grafana/Prometheus/Jaeger/OTEL manifests)
- scripts/ (local helper scripts)
- dump.py (utility to export repo content)

Observed network state (from cluster queries)
- Istio ingress service: `istio-ingressgateway` in `istio-system`
  - Type: LoadBalancer
  - Cluster IP: 10.110.100.6
  - LoadBalancer Ingress: 127.0.0.1 (local tunnel typical of Minikube)
  - NodePorts (examples): http -> 32086, https -> 31606
  - Endpoints: pod IP 10.244.0.206
- Gateway: `leninkart-gateway` (namespace `dev`)
- Ingress pod: `istio-ingressgateway-...` running on node `minikube`

How traffic flows (network layer)
1. Client (browser / curl) -> Istio IngressGateway service (external IP or nodePort or port-forward)
2. Istio Gateway resource defines which ports and hosts are accepted
3. VirtualService binds to Gateway and maps host+path to a Destination (K8s Service)
4. Kubernetes Service routes traffic to healthy Pod endpoints
5. Application responds; metrics/logs are recorded and can be observed via `observability/` tools

How to access applications (PowerShell examples)
Note: These examples assume you have `kubectl` configured to point at the cluster where `leninkart` is deployed. Replace `<HOST>` and `<PATH>` with values from your VirtualService.

1) Quick discovery (to run first)
```powershell
kubectl -n istio-system get svc istio-ingressgateway -o wide
kubectl -n istio-system describe svc istio-ingressgateway
kubectl get gateway -A
kubectl -n dev describe gateway leninkart-gateway
kubectl -n dev get virtualservice -o wide
kubectl -n dev describe virtualservice <virtualservice-name>
kubectl -n istio-system get pods -l app=istio-ingressgateway -o wide
```

2) Minikube / Local (observed setup: LB -> 127.0.0.1, nodePorts available)
- Direct to NodePort (if nodePort exposed and accessible on localhost):
```powershell
# HTTP
curl.exe -v -H "Host: <HOST_FROM_VS>" http://127.0.0.1:32086/<PATH>
# HTTPS (insecure skip verification for testing)
curl.exe -vk -H "Host: <HOST_FROM_VS>" https://127.0.0.1:31606/<PATH>
```
- Port-forward ingressgateway to local ports (reliable when node ports aren't reachable):
```powershell
kubectl -n istio-system port-forward svc/istio-ingressgateway 8080:80 8443:443
# then
curl.exe -v -H "Host: <HOST_FROM_VS>" http://localhost:8080/<PATH>
```
- If Gateway expects TLS and hostname SNI, use `--resolve` or `--header` on curl:
```powershell
curl.exe -vk --resolve <HOST>:443:127.0.0.1 https://<HOST>/<PATH>
```

3) Cloud (GKE/EKS/AKS) — if LoadBalancer EXTERNAL-IP is public
```powershell
# When EXTERNAL-IP exists
curl.exe -v -H "Host: <HOST_FROM_VS>" http://<EXTERNAL_IP>:80/<PATH>
# or
curl.exe -vk --resolve <HOST>:443:<EXTERNAL_IP> https://<HOST>/<PATH>
```

Determining Host and Path
- VirtualService `hosts` defines the Host header value you must supply. If the VS routes by path only, Host may be `*` and you can hit IP directly (but many setups require Host).
- Example to extract hosts from VirtualServices in `dev`:
```powershell
kubectl -n dev get virtualservice -o yaml | Select-String -Pattern 'hosts|gateways|http' -Context 0,3
```

Troubleshooting (common errors and fixes)
- 404 / 503 responses:
  - Check VirtualService routes and ensure they reference the correct Service.
  - Check `kubectl get endpoints <service> -n <ns>` to ensure pods are ready.
- Host header mismatch: add `-H "Host: <host>"` to curl or add an entry to your Windows hosts file mapping host -> EXTERNAL_IP.
- TLS/SNI: if Gateway expects TLS, use `--resolve` with curl or configure DNS + valid cert.
- Minimal debugging commands:
```powershell
kubectl -n dev describe virtualservice <vs-name>
kubectl -n dev describe gateway leninkart-gateway
kubectl -n istio-system logs -l app=istio-ingressgateway --tail=200
istioctl analyze
```

Security & hygiene findings
- Backups and temporary files existed (`_cleanup_backup/`, `_ingress_backup/`) — I removed those from the working tree and added `.gitignore` entries.
- File `voult.py` looks like a potential typo for `vault.py` — search for usages before renaming.
- Repo contains `postgres-secret.yaml` under `platform/postgres/` — ensure there are no plaintext secrets committed. If you find any secrets, rotate them and remove from history.
- A directory name contains a non-ASCII character `ervability stack` which could cause tooling issues — consider renaming.

Prioritized recommendations (short list)
1. Immediate (low risk)
   - Run a secrets scan (gitleaks/gitleaks++/trufflehog) and remove or rotate any secrets found.
   - Add and enforce `.gitignore` patterns for backup files and local dumps (already updated in this session).
   - Add a `docs/NETWORK_ACCESS.md` (or use this file) so new devs can find the steps to access services.
2. Short-term (next 1–2 days)
   - Add CI checks: YAML lint, helm lint, kubeval, and unit tests for charts.
   - Add pre-commit hooks: black/flake8 for Python, yamllint, secret detection.
   - Search and validate `voult.py` typo and correct if unused.
3. Medium-term
   - Centralize dev values or use a `helmfile` for consistent values across environments.
   - Ensure ExternalSecrets + Vault are used in place of committed secrets.
4. Long-term
   - Add automated validation and policy checks (OPA Gatekeeper/Conftest) in CI.
   - Add chart-testing and integration tests for ArgoCD app deployments.

Suggested actionable next steps I can take now
- Create `docs/NETWORK_ACCESS.md` (done — this file may be added as a separate concise doc if you prefer).
- Run a secrets scan and provide a report with matches.
- Describe the `leninkart-gateway` and enumerate VirtualServices and produce exact curl commands for each app (I can run these kubectl commands now and add them to the doc).
- Add a small `scripts/access-leninkart.ps1` that port-forwards and runs smoke curl tests.

How I verified
- Ran `kubectl` commands from your workspace (PowerShell) to inspect the `istio-ingressgateway` service, gateway resources, and ingress pod. Observed Minikube node and local LB mapping.

If you want me to continue
- I can now run `kubectl -n dev describe gateway leninkart-gateway` and list VirtualServices in `dev` to extract exact hosts/paths and add direct curl commands to this document. 
- I can run a secrets scan and deliver a report.
- I can create a small helper script to automate port-forward + smoke tests.

Tell me which of the above to do next (describe gateway & vs; run secrets scan; add helper script; push docs commit to origin). Thanks!
