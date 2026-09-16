import csv
from typing import List, Dict, Any
from pathlib import Path

ERROR_CATEGORIES = {
    "A": "financial-state reconstruction",
    "B": "recurring-income forecasting",
    "C": "recurring-expense forecasting",
    "D": "transaction lifecycle handling",
    "E": "FX conversion",
    "F": "payment-plan optimization",
    "G": "date arithmetic",
    "H": "evidence extraction",
    "I": "user preferences",
    "J": "explanation generation",
    "K": "validation",
    "L": "routing"
}

def analyze_errors(predictions: List[Dict[str, Any]], ground_truth: List[Dict[str, Any]], output_csv: Path):
    """
    Compares predictions against ground truth and catalogs errors.
    This requires a manual mapping or rule-based heuristic to assign root causes,
    but for now it sets up the structure required by Phase 3.
    """
    errors = []
    
    for pred, gt in zip(predictions, ground_truth):
        p_status = pred.get("status", "")
        g_status = gt.get("status", "")
        p_method = pred.get("method", "")
        g_method = gt.get("method", "")
        p_amount = float(pred.get("amount", 0.0))
        g_amount = float(gt.get("amount", 0.0))
        
        if p_status != g_status or p_method != g_method or abs(p_amount - g_amount) > 1e-2:
            # Simple heuristic for error categorization (to be expanded in forensics)
            category = "Unknown"
            if p_status != g_status:
                category = "C" # Default to recurring expense forecasting failure causing affordability status drop
            elif p_method != g_method:
                category = "F" # Plan optimization failure
            elif abs(p_amount - g_amount) > 1e-2:
                category = "A" # State reconstruction / balance failure
                
            errors.append({
                "request_id": pred.get("request_id", "unknown"),
                "pred_status": p_status,
                "gt_status": g_status,
                "pred_amount": p_amount,
                "gt_amount": g_amount,
                "error_category": category,
                "category_desc": ERROR_CATEGORIES.get(category, "Unknown")
            })
            
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["request_id", "pred_status", "gt_status", "pred_amount", "gt_amount", "error_category", "category_desc"])
        writer.writeheader()
        writer.writerows(errors)
    
    return errors
