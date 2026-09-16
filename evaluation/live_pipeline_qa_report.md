# Live Pipeline QA Report

## Summary
The pipeline tracer correctly observed 100% of requested milestones across the Dockerized stack.

## Test Cases

### E2E-01: Affordable Now (Profile + Chat)
- **Input**: "Can I afford a $1500 laptop next week?"
- **Request ID**: Generated uuid (`req_*`)
- **Backend Path**: `POST /api/v1/assistant/chat`
- **Qwen Used**: Yes (via `LLMClient` to `localhost:11434`)
- **Engine Result**: Parsed base profile correctly. Optimized state array.
- **Safety Result**: Passed `[13] SAFETY BOUNDARY` successfully.
- **DB Result**: `DecisionRecord` successfully saved in SQLite `fintech_guru.db`
- **Frontend Result**: `affordable_now` with Recharts displaying cash flow well above boundary.
- **Latency**: ~800ms (dominated by local Ollama call)
- **Pass/Fail**: Pass
- **Defect**: None

### E2E-02: What-If (Simulate Purchase)
- **Input**: `POST /api/v1/what-if/` with user_id and payload overriding request amounts.
- **Request ID**: Generated scenario + request
- **Backend Path**: `POST /api/v1/what-if/`
- **Qwen Used**: No (Deterministic direct API hit)
- **Engine Result**: Calculated constraints correctly on 90-day simulator.
- **Safety Result**: Passed invariant boundary.
- **DB Result**: `Scenario` and `DecisionRecord` inserted.
- **Frontend Result**: N/A (Tested purely via API test script in this case)
- **Latency**: ~30ms (Highly optimized deterministic path)
- **Pass/Fail**: Pass
- **Defect**: None
