# Environment Definitions

FinTech Guru V2 enforces distinct configurations across four canonical environments: `development`, `test`, `staging`, and `production`.

## Environment Isolation Rules
- **Development**: Runs locally. Defaults to `sqlite`, `local` storage backend, and local `Ollama`. 
- **Test**: Used heavily in CI (`.github/workflows`). Leverages mock LLMs and temporary SQLite databases.
- **Staging**: A mirror of production. Uses PostgreSQL, S3, and real cloud GPUs (or dedicated Ollama servers), but with dummy users.
- **Production**: Live. Must never use `localhost` endpoints. Requires strict `SECRET_KEY`, `CORS_ORIGINS`, and production PostgreSQL.

## Validation Strategy
The system utilizes `pydantic-settings` via `app/config.py`.
If required variables (like `DATABASE_URL`) are malformed, or if `S3_BUCKET_NAME` is missing while `STORAGE_BACKEND=s3`, the application will **fail fast** at startup rather than throwing silent runtime errors.

## Secrets Management
- Secrets (`SECRET_KEY`, `AWS_SECRET_ACCESS_KEY`) must never be hardcoded or committed to git.
- For Docker deployments, secrets are injected via `.env` files (ignored in git) or CI/CD Secret Managers.
