from __future__ import annotations

import argparse
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger('observer-agent')


@dataclass
class AgentConfig:
    cluster_id: str
    central_push_url: str
    agent_token: str
    local_prometheus_url: str
    local_otel_metrics_url: str
    poll_interval_seconds: int
    timeout_seconds: int
    prom_queries: list[tuple[str, str]]


DEFAULT_QUERIES = [
    ('up_count', 'sum(up)'),
    ('cpu_usage_pct', '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'),
    ('http_5xx_rate', 'sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))'),
]


def _parse_queries(raw: str | None) -> list[tuple[str, str]]:
    if not raw:
        return DEFAULT_QUERIES
    parsed: list[tuple[str, str]] = []
    for item in raw.split(';'):
        part = item.strip()
        if not part:
            continue
        if '=' not in part:
            parsed.append((part.replace(' ', '_'), part))
            continue
        name, expr = part.split('=', 1)
        parsed.append((name.strip(), expr.strip()))
    return parsed or DEFAULT_QUERIES


def load_config() -> AgentConfig:
    return AgentConfig(
        cluster_id=os.getenv('CLUSTER_ID', 'minikube-dev'),
        central_push_url=os.getenv('CENTRAL_PUSH_URL', 'http://ai-observer-central-collector.dev.svc.cluster.local:8081/api/agent/push'),
        agent_token=os.getenv('AGENT_TOKEN', 'dev-agent-token'),
        local_prometheus_url=os.getenv('LOCAL_PROMETHEUS_URL', 'http://prometheus.dev.svc.cluster.local:9090'),
        local_otel_metrics_url=os.getenv('LOCAL_OTEL_METRICS_URL', 'http://otel-collector.dev.svc.cluster.local:8889/metrics'),
        poll_interval_seconds=int(os.getenv('POLL_INTERVAL_SECONDS', '30')),
        timeout_seconds=int(os.getenv('HTTP_TIMEOUT_SECONDS', '6')),
        prom_queries=_parse_queries(os.getenv('PROM_QUERIES')),
    )


def query_prometheus(config: AgentConfig) -> list[dict]:
    out: list[dict] = []
    for metric_name, query in config.prom_queries:
        try:
            resp = requests.get(
                f"{config.local_prometheus_url}/api/v1/query",
                params={'query': query},
                timeout=config.timeout_seconds,
            )
            resp.raise_for_status()
            payload = resp.json()
            result = payload.get('data', {}).get('result', [])
            value = float(result[0]['value'][1]) if result else 0.0
        except Exception as exc:  # noqa: BLE001
            logger.warning('prom_query_failed metric=%s err=%s', metric_name, exc)
            value = 0.0

        out.append(
            {
                'name': metric_name,
                'value': value,
                'labels': {'source': 'prometheus'},
                'ts_unix_ms': int(time.time() * 1000),
            }
        )
    return out


def query_otel_summary(config: AgentConfig) -> tuple[list[dict], list[dict], list[dict]]:
    metrics: list[dict] = []
    logs: list[dict] = []
    traces: list[dict] = []

    try:
        resp = requests.get(config.local_otel_metrics_url, timeout=config.timeout_seconds)
        resp.raise_for_status()
        body = resp.text
    except Exception as exc:  # noqa: BLE001
        logger.warning('otel_metrics_pull_failed err=%s', exc)
        body = ''

    accepted_metric_points = _read_prom_metric(body, 'otelcol_receiver_accepted_metric_points')
    accepted_log_records = _read_prom_metric(body, 'otelcol_receiver_accepted_log_records')
    accepted_spans = _read_prom_metric(body, 'otelcol_receiver_accepted_spans')

    metrics.extend(
        [
            {'name': 'otel_accepted_metric_points', 'value': accepted_metric_points, 'labels': {'source': 'otel'}},
            {'name': 'otel_accepted_log_records', 'value': accepted_log_records, 'labels': {'source': 'otel'}},
            {'name': 'otel_accepted_spans', 'value': accepted_spans, 'labels': {'source': 'otel'}},
        ]
    )
    logs.append(
        {
            'message': f'agent heartbeat for cluster {config.cluster_id}',
            'severity': 'info',
            'service': 'observer-agent',
            'labels': {'cluster_id': config.cluster_id},
            'ts_unix_ns': str(int(time.time() * 1_000_000_000)),
        }
    )
    traces.append(
        {
            'operation': 'observer-agent.poll',
            'duration_ms': random.randint(3, 20),
            'service': 'observer-agent',
            'status': 'ok',
            'attributes': {'collector': 'local-otel'},
        }
    )

    return metrics, logs, traces


def _read_prom_metric(body: str, metric_name: str) -> float:
    for line in body.splitlines():
        if not line.startswith(metric_name):
            continue
        if line.startswith('#'):
            continue
        parts = line.strip().split(' ')
        if len(parts) < 2:
            continue
        try:
            return float(parts[-1])
        except ValueError:
            continue
    return 0.0


def build_payload(config: AgentConfig) -> dict:
    prom_metrics = query_prometheus(config)
    otel_metrics, logs, traces = query_otel_summary(config)
    return {
        'cluster_id': config.cluster_id,
        'metrics': prom_metrics + otel_metrics,
        'logs': logs,
        'traces': traces,
        'metadata': {
            'agent': 'observer-agent',
            'mode': 'summary-json',
            'generated_at': datetime.now(timezone.utc).isoformat(),
        },
    }


def push_payload(config: AgentConfig, payload: dict) -> None:
    headers = {
        'Content-Type': 'application/json',
        'X-Agent-Token': config.agent_token,
    }
    response = requests.post(config.central_push_url, headers=headers, data=json.dumps(payload), timeout=config.timeout_seconds)
    response.raise_for_status()
    logger.info('push_ok status=%s cluster_id=%s body=%s', response.status_code, config.cluster_id, response.text)


def main() -> None:
    parser = argparse.ArgumentParser(description='observer-agent telemetry shipper')
    parser.add_argument('--once', action='store_true', help='send one payload and exit')
    args = parser.parse_args()

    config = load_config()
    logger.info('agent_start cluster=%s push_url=%s', config.cluster_id, config.central_push_url)

    while True:
        payload = build_payload(config)
        try:
            push_payload(config, payload)
        except Exception as exc:  # noqa: BLE001
            logger.error('push_failed cluster=%s err=%s', config.cluster_id, exc)

        if args.once:
            break
        time.sleep(config.poll_interval_seconds)


if __name__ == '__main__':
    main()