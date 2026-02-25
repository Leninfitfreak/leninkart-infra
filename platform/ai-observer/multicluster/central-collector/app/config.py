from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'ai-observer-central-collector'
    app_version: str = '0.1.0'

    agent_shared_token: str = 'dev-agent-token'
    otel_collector_base_url: str = 'http://otel-collector:4318'
    loki_push_url: str = 'http://loki:3100/loki/api/v1/push'
    tempo_otlp_http_endpoint: str = 'http://tempo:4318/v1/traces'

    request_timeout_seconds: int = 8
    history_buffer_size: int = 2000


settings = Settings()