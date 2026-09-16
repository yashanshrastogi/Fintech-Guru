import json
from typing import List, Dict, Any

def check_reproducibility(run_a: List[Dict[str, Any]], run_b: List[Dict[str, Any]]) -> float:
    """
    Checks that the deterministic mode yields exactly the same outputs across two identical runs.
    Returns the percentage of identical outputs (1.0 = 100% reproducible).
    """
    if len(run_a) != len(run_b):
        return 0.0
        
    matches = 0
    for a, b in zip(run_a, run_b):
        # Compare key financial outputs
        if (a.get("status") == b.get("status") and 
            a.get("method") == b.get("method") and
            a.get("amount") == b.get("amount") and 
            a.get("plan") == b.get("plan")):
            matches += 1
            
    return matches / len(run_a) if run_a else 1.0
