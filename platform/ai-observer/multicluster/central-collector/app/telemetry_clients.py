from __future__ import annotations

import logging
import time
from collections import defaultdict

import httpx
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .config import settings
from .models import LogRecord, TraceRecord

logger = logging.getLogger(__name__)


class TelemetryRouter:
    def __init__(self) -> None:
        resource = Resource.create({'service.name': settings.app_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.tempo_otlp_http_endpoint)))
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer('central-collector-tracer')

    async def forward_otlp(self, signal: str, payload: bytes, content_type: str) -> int:
        url = f"{settings.otel_collector_base_url}/v1/{signal}"
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(url, content=payload, headers={'content-type': content_type})
            response.raise_for_status()
            return response.status_code

    async def push_logs_to_loki(self, cluster_id: str, logs: list[LogRecord]) -> int:
        if not logs:
            return 0

        streams: dict[tuple[str, str], list[list[str]]] = defaultdict(list)
        for item in logs:
            labels = {'cluster_id': cluster_id, 'service': item.service, 'severity': item.severity}
            key = (item.service, item.severity)
            ts = item.ts_unix_ns or str(int(time.time() * 1_000_000_000))
            streams[key].append([ts, item.message])

        payload_streams = []
        for (service, severity), values in streams.items():
            payload_streams.append(
                {
                    'stream': {'cluster_id': cluster_id, 'service': service, 'severity': severity},
                    'values': values,
                }
            )

        body = {'streams': payload_streams}
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                response = await client.post(settings.loki_push_url, json=body)
                response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logger.warning('failed_to_push_loki cluster=%s err=%s', cluster_id, exc)
            return 0
        return len(logs)

    async def push_traces_to_tempo(self, cluster_id: str, traces: list[TraceRecord]) -> int:
        if not traces:
            return 0

        for item in traces:
            with self._tracer.start_as_current_span(item.operation) as span:
                span.set_attribute('cluster_id', cluster_id)
                span.set_attribute('service.name', item.service)
                span.set_attribute('trace.status', item.status)
                span.set_attribute('trace.duration_ms', item.duration_ms)
                for key, value in item.attributes.items():
                    span.set_attribute(f'custom.{key}', str(value))
        return len(traces)