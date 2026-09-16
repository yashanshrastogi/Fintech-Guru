# FinTech Guru V2 Runbook

## Deployment

### Dependencies
- Docker & Docker Compose
- Host machine capable of running Ollama (8GB+ RAM recommended for Qwen3:8B)

### Build Commands
```bash
docker compose build
docker compose up -d
```

### Environment Variables
- `ENVIRONMENT`: (production | development)
- `DEBUG_PIPELINE_TRACE`: (true | false) - Enables verbose latency and state logging.
- `OLLAMA_BASE_URL`: Pointer to host LLM (default `http://localhost:11434`)
- `OLLAMA_MODEL`: Model name (default `qwen3:8b`)

## Observability & Logging
Logs are automatically persisted to `/app/logs` via the Docker volume mount.
- `logs/audit.jsonl`: Core endpoint hit metrics and overall latency.
- `logs/telemetry.jsonl`: Highly structured output of every node in the pipeline.
- `logs/trace.jsonl`: Sequential trace tree per `request_id`.

## Troubleshooting

**Symptom**: All chats return deterministic responses but no extracted intelligence.
- **Root Cause**: Ollama is unreachable.
- **Fix**: Check `OLLAMA_BASE_URL`. If running Docker on Mac/Windows, use `host.docker.internal:11434`. 

**Symptom**: `OperationalError: no such table`
- **Root Cause**: SQLite database failed to initialize.
- **Fix**: Restart the `backend` container to trigger `Base.metadata.create_all()`.
