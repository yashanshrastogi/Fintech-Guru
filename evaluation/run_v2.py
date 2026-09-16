import json
import argparse
import time
from pathlib import Path
from pydantic import ValidationError

from app.main import AffordabilityRequest
from llm.router import route_request
from app.main import deterministic_pipeline, multi_agent_fallback_handler

def run_v2_engine(dataset_file: Path, output_file: Path):
    with open(dataset_file, "r") as f:
        dataset = [json.loads(line) for line in f]
        
    predictions = []
    
    for record in dataset:
        start_time = time.time()
        
        try:
            req = AffordabilityRequest(**record)
            
            pipeline_result = route_request(
                mode=req.mode,
                deterministic_handler=deterministic_pipeline,
                multi_agent_handler=multi_agent_fallback_handler,
                req=req
            )
            
            latency = (time.time() - start_time) * 1000
            
            plans = pipeline_result["plans"]
            best_plan = plans[0] if plans else None
            
            predictions.append({
                "request_id": req.purchase.request_id,
                "latency_ms": latency,
                "expected_decision": record.get("expected_decision", "unknown"),
                "decision": {
                    "status": pipeline_result["status"],
                    "safe_amount_today": float(pipeline_result["explanation"].safe_amount_today),
                    "is_affordable": pipeline_result["status"] in ["affordable_now", "affordable_with_plan"],
                    "recommended_method": best_plan.method if best_plan else "none",
                    "lowest_projected_balance": float(pipeline_result["explanation"].lowest_projected_balance),
                    "safety_margin": float(pipeline_result["explanation"].safety_margin),
                    "risk_flags": best_plan.risk_flags if best_plan else []
                }
            })
            
        except ValidationError as e:
            print(f"Validation error for record: {e}")
        except Exception as e:
            print(f"Error processing record: {e}")
            
    with open(output_file, "w") as f:
        for p in predictions:
            f.write(json.dumps(p) + "\n")
            
    print(f"Processed {len(predictions)} records. Saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    
    run_v2_engine(args.dataset, args.output)
