from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MetricSample(BaseModel):
    name: str
    value: float
    labels: dict[str, str] = Field(default_factory=dict)
    ts_unix_ms: int | None = None


class LogRecord(BaseModel):
    message: str
    severity: str = 'info'
    service: str = 'unknown'
    ts_unix_ns: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)


class TraceRecord(BaseModel):
    operation: str
    duration_ms: int = 0
    service: str = 'unknown'
    status: str = 'ok'
    attributes: dict[str, Any] = Field(default_factory=dict)


class AgentPushPayload(BaseModel):
    cluster_id: str
    metrics: list[MetricSample] = Field(default_factory=list)
    logs: list[LogRecord] = Field(default_factory=list)
    traces: list[TraceRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PushResponse(BaseModel):
    accepted: bool
    cluster_id: str
    metric_count: int
    log_count: int
    trace_count: int
    otlp_forwarded: bool = False