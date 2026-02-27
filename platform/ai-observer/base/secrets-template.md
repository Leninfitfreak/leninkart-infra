# AI Observer Cloud LLM Secret Template

Create this secret in `dev` namespace with your cloud API key:

```powershell
kubectl -n dev create secret generic ai-observer-secrets `
  --from-literal=OPENAI_API_KEY="<YOUR_API_KEY>" `
  --dry-run=client -o yaml | kubectl apply -f -
```

If you rotate the key, rerun the command and restart deployment:

```powershell
kubectl -n dev rollout restart deploy/ai-observer
```
