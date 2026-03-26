# ArgoCD Repo-Server Recovery Note

## Root Cause

ArgoCD core was originally installed from the local bootstrap script instead of a Git-managed ArgoCD control-plane path in `leninkart-infra`.

The live `argocd-repo-server` deployment used the upstream `copyutil` init container command:

```sh
/bin/cp --update=none /usr/local/bin/argocd /var/run/argocd/argocd && /bin/ln -s /var/run/argocd/argocd /var/run/argocd/argocd-cmp-server
```

When the pod retried init on the same pod volume state, the symlink target already existed and the init container failed with:

```text
/bin/ln: Already exists
```

That left `argocd-repo-server` without ready endpoints, which caused:

- `leninkart-root` `ComparisonError`
- no Git reconciliation
- no creation of the `argocd-config` application
- no application of the Git-managed `accounts.github-actions` account

## Fix Applied

A Git-tracked repo-server recovery patch was added at:

- `ops/argocd-recovery/argocd-repo-server-initcontainer-patch.yaml`

The fix makes the `copyutil` init container idempotent by removing the target files before copy/link creation and using `ln -sf`.

## Recovery Flow

1. Commit and push the Git-tracked patch to `leninkart-infra/dev`.
2. Apply the patch from the Git-tracked file once to recover the ArgoCD control plane itself:

   `kubectl patch deployment argocd-repo-server -n argocd --type strategic --patch-file ops/argocd-recovery/argocd-repo-server-initcontainer-patch.yaml`

3. Wait for `argocd-repo-server` to become Ready and its service to gain endpoints.
4. Allow `leninkart-root` to reconcile the new `argocd-config` application.
5. Verify that the live `argocd-cm` now contains:

```yaml
accounts.github-actions: apiKey, login
```

## Before / After Verification

Before recovery:

- `argocd-repo-server` had no endpoints
- `leninkart-root` reported `ComparisonError`
- `argocd-config` application did not exist
- `argocd-cm` did not contain `accounts.github-actions`

After recovery, verify:

- `kubectl get pods -n argocd`
- `kubectl get svc,endpoints -n argocd`
- `kubectl get application leninkart-root -n argocd -o yaml`
- `kubectl get application argocd-config -n argocd -o yaml`
- `kubectl get configmap argocd-cm -n argocd -o yaml`
