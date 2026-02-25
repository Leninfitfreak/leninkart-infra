# Central Collector

FastAPI service for additive multi-cluster ingestion.

## Endpoint

- `POST /api/agent/push`
  - auth header: `X-Agent-Token`
  - supports:
    - `application/json` summary payload
    - `application/x-protobuf` OTLP passthrough (requires `X-OTLP-Signal: metrics|logs|traces`)

## Run local

```powershell
cd platform/ai-observer/multicluster/central-collector
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8081
```