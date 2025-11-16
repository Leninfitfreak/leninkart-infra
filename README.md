# Leninkart App-of-Apps (example)

This repo subtree contains example Helm charts for 3 services and an ArgoCD App-of-Apps setup.

**You must update** the following placeholders before use:
- Replace `https://github.com/YOUR_ORG/YOUR_REPO.git` with your repository URL in the ArgoCD manifests.
- Replace image repository values in each chart `values.yaml` with your actual Artifact Registry / Container Registry paths.
- Adjust namespaces and resource values as needed.

## Structure
- helm/<service> - Helm chart for each service (deployment + service)
- argocd/root-application.yaml - The App-of-Apps root Application
- argocd/apps/* - Child Application manifests for each Helm chart

## How to use
1. Push these files into your Git repo (root of the repo).
2. Update placeholders above.
3. Install ArgoCD in your cluster (namespace `argocd`) and apply `argocd/root-application.yaml`.
4. ArgoCD will create child Applications from `argocd/apps/` and deploy Helm charts from `helm/*`.
