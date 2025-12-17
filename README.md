# LeninKart Infrastructure (GitOps)

This repository contains Helm charts and Argo CD App-of-Apps configuration
for deploying LeninKart microservices across **dev**, **staging**, and **prod**
environments using **branch-based GitOps**.

## Branch → Environment Mapping
- dev     → dev namespace
- staging → staging namespace
- main    → prod namespace

CI updates image tags in this repo.
Argo CD reconciles the desired state automatically.
