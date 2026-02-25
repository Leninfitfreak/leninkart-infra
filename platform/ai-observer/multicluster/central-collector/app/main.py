from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Gauge, make_asgi_app

from .config import settings
from .models import AgentPushPayload, PushResponse
from .store import EventStore
from .telemetry_clients import TelemetryRouter

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.mount('/metrics', make_asgi_app())

push_requests = Counter('observer_agent_ingest_requests', 'Ingestion requests', ['status', 'mode'])
push_metrics = Counter('observer_agent_metric_samples', 'Metric samples accepted', ['cluster_id'])
push_logs = Counter('observer_agent_log_records', 'Log records accepted', ['cluster_id'])
push_traces = Counter('observer_agent_trace_records', 'Trace records accepted', ['cluster_id'])
latest_metric_value = Gauge('observer_agent_latest_metric_value', 'Latest agent metric values', ['cluster_id', 'metric_name'])

store = EventStore(maxlen=settings.history_buffer_size)
router = TelemetryRouter()


def _check_token(token: str | None) -> None:
    if token != settings.agent_shared_token:
        push_requests.labels(status='unauthorized', mode='unknown').inc()
        raise HTTPException(status_code=401, detail='invalid_agent_token')


@app.get('/healthz')
def healthz() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/api/agent/push', response_model=PushResponse)
async def agent_push(
    request: Request,
    x_agent_token: str | None = Header(default=None, alias='X-Agent-Token'),
    x_otlp_signal: str | None = Header(default=None, alias='X-OTLP-Signal'),
) -> PushResponse:
    _check_token(x_agent_token)
    content_type = request.headers.get('content-type', '')

    if 'application/x-protobuf' in content_type:
        signal = (x_otlp_signal or '').strip().lower()
        if signal not in {'metrics', 'logs', 'traces'}:
            push_requests.labels(status='bad_request', mode='otlp').inc()
            raise HTTPException(status_code=400, detail='missing_or_invalid_x_otlp_signal')

        body = await request.body()
        try:
            code = await router.forward_otlp(signal=signal, payload=body, content_type='application/x-protobuf')
        except Exception as exc:  # noqa: BLE001
            push_requests.labels(status='upstream_error', mode='otlp').inc()
            logger.error('otlp_forward_failed signal=%s err=%s', signal, exc)
            raise HTTPException(status_code=502, detail='otlp_forward_failed') from exc
        push_requests.labels(status='accepted', mode='otlp').inc()
        logger.info('otlp_forwarded signal=%s status=%s bytes=%s', signal, code, len(body))
        return PushResponse(
            accepted=True,
            cluster_id='unknown',
            metric_count=0,
            log_count=0,
            trace_count=0,
            otlp_forwarded=True,
        )

    try:
        raw_json = await request.json()
    except Exception as exc:  # noqa: BLE001
        push_requests.labels(status='bad_request', mode='json').inc()
        raise HTTPException(status_code=400, detail='invalid_json_payload') from exc

    payload = AgentPushPayload.model_validate(raw_json)
    cluster_id = payload.cluster_id

    for item in payload.metrics:
        latest_metric_value.labels(cluster_id=cluster_id, metric_name=item.name).set(item.value)

    logs_written = await router.push_logs_to_loki(cluster_id=cluster_id, logs=payload.logs)
    traces_written = await router.push_traces_to_tempo(cluster_id=cluster_id, traces=payload.traces)

    push_metrics.labels(cluster_id=cluster_id).inc(len(payload.metrics))
    push_logs.labels(cluster_id=cluster_id).inc(logs_written)
    push_traces.labels(cluster_id=cluster_id).inc(traces_written)
    push_requests.labels(status='accepted', mode='json').inc()

    event = {
        'cluster_id': cluster_id,
        'metric_count': len(payload.metrics),
        'log_count': logs_written,
        'trace_count': traces_written,
        'metadata': payload.metadata,
        'ingested_at': datetime.now(timezone.utc).isoformat(),
    }
    store.add(event)
    logger.info(
        'agent_push_accepted cluster=%s metrics=%s logs=%s traces=%s',
        cluster_id,
        len(payload.metrics),
        logs_written,
        traces_written,
    )

    return PushResponse(
        accepted=True,
        cluster_id=cluster_id,
        metric_count=len(payload.metrics),
        log_count=logs_written,
        trace_count=traces_written,
    )


@app.get('/api/observability/history')
def observability_history(
    cluster: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> JSONResponse:
    events = store.list(cluster=cluster, limit=limit)
    return JSONResponse({'cluster': cluster, 'items': events, 'count': len(events)})


@app.get('/api/observability/dashboard')
def observability_dashboard(cluster: str | None = Query(default=None)) -> JSONResponse:
    summary = store.aggregate(cluster=cluster)
    return JSONResponse({'cluster': cluster, 'summary': summary})
