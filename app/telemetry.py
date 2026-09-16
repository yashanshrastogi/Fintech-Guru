import logging
import json
import os
import time

logger = logging.getLogger("fintechguru.telemetry")

class PipelineTracer:
    def __init__(self, request_id: str, user_id: str):
        self.request_id = request_id
        self.user_id = user_id
        self.trace_enabled = os.environ.get("DEBUG_PIPELINE_TRACE", "false").lower() == "true"
        self.stages = []
        self.start_time = time.time()
        self.telemetry = {
            "request_id": request_id,
            "session_id": "sess_default",
            "timestamp": self.start_time,
            "endpoint": "",
            "route": "",
            "latency": 0.0,
            "input_validation_status": "pending",
            "evidence_required": False,
            "qwen_attempted": False,
            "qwen_success": False,
            "qwen_failure": False,
            "qwen_latency_ms": 0.0,
            "router_reason": "default",
            "reconciliation_status": "pending",
            "forecast_status": "pending",
            "simulator_status": "pending",
            "optimizer_status": "pending",
            "planner_status": "pending",
            "safety_boundary_status": "pending",
            "decision_status": "pending",
            "persistence_status": "pending",
            "frontend_response_status": "pending"
        }

    def record_stage(self, stage_name: str, status: str, duration_ms: float = 0.0, metadata: dict = None, error: str = None):
        if self.trace_enabled:
            stage_data = {
                "stage": stage_name,
                "duration_ms": duration_ms,
                "status": status,
                "metadata": metadata or {},
                "error": error
            }
            self.stages.append(stage_data)
            logger.info(f"[TRACE] {self.request_id} | {stage_name}: {status} | {duration_ms}ms")

        # Update telemetry fields dynamically based on stage
        field_map = {
            "[03] VALIDATION": "input_validation_status",
            "[06] EVIDENCE": "qwen_success" if status == "success" else "qwen_failure",
            "[08] RECONCILIATION": "reconciliation_status",
            "[09] FORECAST": "forecast_status",
            "[10] SIMULATION": "simulator_status",
            "[11] OPTIMIZATION": "optimizer_status",
            "[12] PLAN": "planner_status",
            "[13] SAFETY BOUNDARY": "safety_boundary_status",
            "[14] DECISION": "decision_status",
            "[15] DATABASE": "persistence_status",
            "[17] FRONTEND RENDER": "frontend_response_status"
        }
        
        if stage_name in field_map:
            field = field_map[stage_name]
            if field == "qwen_success":
                self.telemetry["qwen_success"] = True
            elif field == "qwen_failure":
                self.telemetry["qwen_failure"] = True
            else:
                self.telemetry[field] = status
                
    def finalize(self):
        self.telemetry["latency"] = (time.time() - self.start_time) * 1000
        os.makedirs("logs", exist_ok=True)
        try:
            with open("logs/telemetry.jsonl", "a") as f:
                f.write(json.dumps(self.telemetry) + "\n")
            if self.trace_enabled:
                with open("logs/trace.jsonl", "a") as f:
                    f.write(json.dumps({"request_id": self.request_id, "stages": self.stages}) + "\n")
        except Exception as e:
            logger.error(f"Failed to write telemetry: {e}")

_active_tracers = {}

def get_tracer(request_id: str, user_id: str = "unknown") -> PipelineTracer:
    if request_id not in _active_tracers:
        _active_tracers[request_id] = PipelineTracer(request_id, user_id)
    return _active_tracers[request_id]

def finalize_tracer(request_id: str):
    if request_id in _active_tracers:
        _active_tracers[request_id].finalize()
        del _active_tracers[request_id]
