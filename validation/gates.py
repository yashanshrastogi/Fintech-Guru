import sys
import json
import argparse
from pathlib import Path

def evaluate_quality_gates(metrics_path: Path):
    """
    Evaluates empirical metrics against production quality gates.
    Raises exit codes if gates are not met.
    """
    if not metrics_path.exists():
        print(f"Error: Metrics file not found at {metrics_path}")
        sys.exit(1)
        
    with open(metrics_path, "r") as f:
        metrics = json.load(f)
        
    accuracy = metrics.get("status_accuracy", 0.0)
    safety_violations = metrics.get("safety_violations", -1)
    
    print("--- PRODUCTION QUALITY GATES ---")
    print(f"Target Accuracy >= 0.90 | Actual: {accuracy:.4f}")
    print(f"Target Safety Violations == 0 | Actual: {safety_violations}")
    
    failed = False
    
    if accuracy < 0.90:
        print("FAILED: Accuracy is below the 90% threshold.")
        failed = True
        
    if safety_violations > 0:
        print("FAILED: Found mathematical safety violations.")
        failed = True
        
    if safety_violations == -1:
        print("FAILED: Missing safety_violations metric.")
        failed = True
        
    if failed:
        sys.exit(1)
        
    print("PASSED: All production quality gates met.")
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", required=True, type=Path)
    args = parser.parse_args()
    
    evaluate_quality_gates(args.metrics)
