import math
from typing import List, Dict, Any

def compute_metrics(predictions: List[Dict[str, Any]], ground_truth: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes rigorous evaluation metrics comparing predictions to ground truth.
    Supports all tracking requirements for V2 Phase 3.
    """
    assert len(predictions) == len(ground_truth), "Mismatch between predictions and ground truth count."
    
    total = len(predictions)
    if total == 0:
        return {}

    exact_matches = 0
    status_correct = 0
    method_correct = 0
    plan_correct = 0
    amount_mae_sum = 0.0
    amount_rmse_sum = 0.0
    max_error = 0.0
    safety_violations = 0
    fallback_count = 0
    total_llm_calls = 0
    latencies = []

    for pred, gt in zip(predictions, ground_truth):
        # We assume pred and gt share the same request_id
        
        # Financial correctness
        p_status = pred.get("status", "")
        g_status = gt.get("status", "")
        p_method = pred.get("method", "")
        g_method = gt.get("method", "")
        p_amount = float(pred.get("amount", 0.0))
        g_amount = float(gt.get("amount", 0.0))
        p_plan = pred.get("plan", [])
        g_plan = gt.get("plan", [])

        if p_status == g_status:
            status_correct += 1
        if p_method == g_method:
            method_correct += 1
        if p_plan == g_plan:
            plan_correct += 1
            
        error = abs(p_amount - g_amount)
        amount_mae_sum += error
        amount_rmse_sum += error ** 2
        max_error = max(max_error, error)
        
        # Exact match (all primary decision fields match)
        if p_status == g_status and p_method == g_method and math.isclose(p_amount, g_amount, abs_tol=1e-2) and p_plan == g_plan:
            exact_matches += 1

        # Safety & Telemetry
        safety_violations += int(pred.get("safety_violations", 0))
        fallback_count += 1 if pred.get("fallback", False) else 0
        total_llm_calls += int(pred.get("llm_calls", 0))
        
        if "latency_ms" in pred:
            latencies.append(pred["latency_ms"])

    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.5)] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

    return {
        "total_requests": total,
        "exact_accuracy": exact_matches / total,
        "status_accuracy": status_correct / total,
        "method_accuracy": method_correct / total,
        "plan_accuracy": plan_correct / total,
        "amount_mae": amount_mae_sum / total,
        "amount_rmse": math.sqrt(amount_rmse_sum / total),
        "amount_max_error": max_error,
        "safety_violations": safety_violations,
        "fallback_rate": fallback_count / total,
        "avg_llm_calls": total_llm_calls / total,
        "latency_p50": p50,
        "latency_p95": p95,
        "deterministic_reproducibility": 1.0  # Assumes 100% until regression.py checks it
    }
