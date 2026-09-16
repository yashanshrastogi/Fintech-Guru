# FinTech Guru V2

FinTech Guru V2 is a fully deterministic, agentic affordability engine with hard safety boundaries. It combines natural language understanding (via Qwen3:8B locally) with a highly rigorous mathematical forecasting model to help users answer a simple question: "Can I afford this?"

## Architecture
- **Frontend**: Next.js 14, Recharts, Tailwind CSS. Provides multi-turn chat and 90-day cashflow visualization.
- **Backend API**: FastAPI, SQLAlchemy (SQLite), Pydantic. Handles endpoints and serialization.
- **Deterministic Engine**: 90-day P90 expense forecaster, anchored salary projector, and payment plan optimizer.
- **LLM Boundary**: Uses Ollama (Qwen3:8B) for natural language extraction of intents. **The LLM is strictly prohibited from bypassing the invariant boundary check.**

## Quick Start (Docker)
1. Install Docker Desktop.
2. Install Ollama and pull `qwen3:8b`.
   ```bash
   ollama serve &
   ollama run qwen3:8b
   ```
3. Run the orchestration:
   ```bash
   docker compose up -d --build
   ```
4. Access the frontend at [http://localhost:3000](http://localhost:3000).

## Repository Map
- `app/engine.py` -> The deterministic numerical core and simulator.
- `app/api/endpoints/` -> Decoupled FastAPI controllers.
- `app/telemetry.py` -> E2E Pipeline Observability (`DEBUG_PIPELINE_TRACE`).
- `frontend/` -> Next.js React codebase.
- `core/` -> Canonical Pydantic schemas.
- `evaluation/` -> Final metrics, holdout test results, and QA reports.

## Safety & Trust
FinTech Guru enforces a **Hard Safety Boundary**. The engine computationally verifies every scenario, ensuring the user's balance will *never* drop below their designated minimum threshold at any point in a 90-day sliding window. LLM prompt injections cannot bypass this mathematical gate.
