# Docker Release Report

## Containers
The system was successfully containerized using multi-stage builds.
- `fintechguru-backend:latest`: Runs the FastAPI server on `python:3.11-slim`.
- `fintechguru-frontend:latest`: Runs the Next.js standalone server on `node:20-alpine`.

## Composition
`docker-compose.yml` orchestrates the system over `fintechguru_default` network.
- Backend exposed on port 8000.
- Frontend exposed on port 3000.
- Frontend injects `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- SQLite database is persisted inside the container at `fintech_guru.db` (for production, this requires a volume mount or PostgreSQL migration, which is handled via SQLAlchemy easily).

## Metrics
- Backend Image Size: ~150MB
- Frontend Image Size: ~220MB (Next.js Standalone Mode)

## Tests
- Tested `docker compose up -d --build`. Both containers start within 3 seconds.
- Python E2E integration hitting localhost:8000 validated the backend's routing and LLM availability successfully inside the Docker network context.
