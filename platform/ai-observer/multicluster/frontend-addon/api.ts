export async function fetchHistory(baseUrl: string, cluster?: string) {
  const query = cluster ? `?cluster=${encodeURIComponent(cluster)}` : '';
  const res = await fetch(`${baseUrl}/api/observability/history${query}`);
  if (!res.ok) {
    throw new Error(`history failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchDashboard(baseUrl: string, cluster?: string) {
  const query = cluster ? `?cluster=${encodeURIComponent(cluster)}` : '';
  const res = await fetch(`${baseUrl}/api/observability/dashboard${query}`);
  if (!res.ok) {
    throw new Error(`dashboard failed: ${res.status}`);
  }
  return res.json();
}