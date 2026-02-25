# Frontend Cluster Filter Addon

This addon is additive and keeps legacy behavior:
- If `cluster` query parameter is omitted, API returns default/unfiltered response.
- If `cluster=<id>` is provided, API returns cluster-scoped data.

## Integration

1. Add `ClusterFilter` to existing dashboard page.
2. Use `fetchHistory` and `fetchDashboard` helpers to call the backend.
3. Do not pass `cluster` initially to preserve current single-cluster behavior.