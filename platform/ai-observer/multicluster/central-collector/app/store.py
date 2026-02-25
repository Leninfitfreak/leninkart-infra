from __future__ import annotations

from collections import deque
from typing import Any


class EventStore:
    def __init__(self, maxlen: int = 2000) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def add(self, event: dict[str, Any]) -> None:
        self._events.appendleft(event)

    def list(self, cluster: str | None, limit: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for item in self._events:
            if cluster and item.get('cluster_id') != cluster:
                continue
            out.append(item)
            if len(out) >= limit:
                break
        return out

    def aggregate(self, cluster: str | None) -> dict[str, int]:
        metrics = 0
        logs = 0
        traces = 0
        events = 0
        for item in self._events:
            if cluster and item.get('cluster_id') != cluster:
                continue
            events += 1
            metrics += int(item.get('metric_count', 0))
            logs += int(item.get('log_count', 0))
            traces += int(item.get('trace_count', 0))
        return {
            'events': events,
            'metrics': metrics,
            'logs': logs,
            'traces': traces,
        }