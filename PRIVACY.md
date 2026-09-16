# Privacy Policy

FinTech Guru V2 operates on a principle of absolute financial privacy. 

## Data Storage
- All decisions, interactions, evidence, and states are stored locally in the persistent `fintech_guru.db` SQLite database.
- We do not transmit financial data to third-party telemetric services.

## Language Model Data
- Our extraction engine utilizes local, on-premise Large Language Models (Qwen3:8B via Ollama).
- No sensitive user financial data is ever sent to OpenAI, Anthropic, Google, or any external API. All extraction happens entirely within the Docker boundary of your local machine.

## Telemetry
- The `DEBUG_PIPELINE_TRACE` functionality strictly logs stage transitions, latencies, and statuses. 
- It actively strips sensitive financial payload values from output logs.
