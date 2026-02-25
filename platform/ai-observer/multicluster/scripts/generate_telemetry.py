from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime, timezone

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate sample telemetry for central collector')
    parser.add_argument('--url', default='http://127.0.0.1:8081/api/agent/push')
    parser.add_argument('--token', default='dev-agent-token')
    parser.add_argument('--cluster', default='minikube-dev')
    parser.add_argument('--count', type=int, default=5)
    args = parser.parse_args()

    headers = {'Content-Type': 'application/json', 'X-Agent-Token': args.token}
    for idx in range(args.count):
        payload = {
            'cluster_id': args.cluster,
            'metrics': [
                {'name': 'synthetic_qps', 'value': random.uniform(10, 120), 'labels': {'service': 'test-generator'}},
                {'name': 'synthetic_error_rate', 'value': random.uniform(0, 5), 'labels': {'service': 'test-generator'}},
            ],
            'logs': [
                {
                    'message': f'synthetic log #{idx}',
                    'severity': 'info',
                    'service': 'test-generator',
                    'ts_unix_ns': str(int(time.time() * 1_000_000_000)),
                }
            ],
            'traces': [
                {
                    'operation': 'synthetic.request',
                    'duration_ms': random.randint(5, 120),
                    'service': 'test-generator',
                    'status': 'ok',
                    'attributes': {'iteration': idx},
                }
            ],
            'metadata': {'generated_at': datetime.now(timezone.utc).isoformat()},
        }
        response = requests.post(args.url, data=json.dumps(payload), headers=headers, timeout=10)
        response.raise_for_status()
        print(response.json())


if __name__ == '__main__':
    main()