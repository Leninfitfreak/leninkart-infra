import sys
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / 'central-collector'))

from app.main import app, router, store  # noqa: E402


client = TestClient(app)


def test_push_requires_token() -> None:
    response = client.post('/api/agent/push', json={'cluster_id': 'dev-1'})
    assert response.status_code == 401


def test_push_and_cluster_filters() -> None:
    router.push_logs_to_loki = AsyncMock(return_value=1)
    router.push_traces_to_tempo = AsyncMock(return_value=1)

    payload_a = {
        'cluster_id': 'cluster-a',
        'metrics': [{'name': 'up_count', 'value': 4.0, 'labels': {'service': 'api'}}],
        'logs': [{'message': 'ok', 'severity': 'info', 'service': 'svc-a'}],
        'traces': [{'operation': 'request', 'duration_ms': 15, 'service': 'svc-a'}],
    }
    payload_b = {
        'cluster_id': 'cluster-b',
        'metrics': [{'name': 'up_count', 'value': 2.0, 'labels': {'service': 'api'}}],
    }

    headers = {'X-Agent-Token': 'dev-agent-token'}
    resp_a = client.post('/api/agent/push', json=payload_a, headers=headers)
    resp_b = client.post('/api/agent/push', json=payload_b, headers=headers)

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    default_history = client.get('/api/observability/history')
    cluster_a_history = client.get('/api/observability/history?cluster=cluster-a')

    assert default_history.status_code == 200
    assert cluster_a_history.status_code == 200
    assert default_history.json()['count'] >= 2
    assert cluster_a_history.json()['count'] >= 1
    assert all(item['cluster_id'] == 'cluster-a' for item in cluster_a_history.json()['items'])

    dashboard_default = client.get('/api/observability/dashboard')
    dashboard_b = client.get('/api/observability/dashboard?cluster=cluster-b')

    assert dashboard_default.status_code == 200
    assert dashboard_b.status_code == 200
    assert dashboard_b.json()['summary']['events'] >= 1

    # keep store bounded for test repeats
    store.list(cluster=None, limit=1)