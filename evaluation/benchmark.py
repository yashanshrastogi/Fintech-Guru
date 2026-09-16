import json
import argparse
from pathlib import Path
from evaluation.metrics import compute_metrics
from evaluation.error_analysis import analyze_errors

def run_benchmark(predictions_file: Path, ground_truth_file: Path, report_dir: Path):
    """
    Main entrypoint for evaluating a model run against ground truth.
    Generates a full metrics report and an error forensics catalog.
    """
    report_dir.mkdir(parents=True, exist_ok=True)
    
    with open(predictions_file, "r") as f:
        predictions = [json.loads(line) for line in f]
        
    with open(ground_truth_file, "r") as f:
        ground_truth = [json.loads(line) for line in f]
        
    metrics = compute_metrics(predictions, ground_truth)
    
    # Save metrics
    metrics_path = report_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
        
    # Analyze errors
    error_csv_path = report_dir / "error_catalog.csv"
    analyze_errors(predictions, ground_truth, error_csv_path)
    
    # Generate human readable report
    report_md = report_dir / "baseline.md"
    with open(report_md, "w") as f:
        f.write("# Benchmark Report\n\n")
        f.write(f"- Total Requests: {metrics.get('total_requests')}\n")
        f.write(f"- Exact Accuracy: {metrics.get('exact_accuracy', 0):.1%}\n")
        f.write(f"- Status Accuracy: {metrics.get('status_accuracy', 0):.1%}\n")
        f.write(f"- Method Accuracy: {metrics.get('method_accuracy', 0):.1%}\n")
        f.write(f"- Plan Accuracy: {metrics.get('plan_accuracy', 0):.1%}\n")
        f.write(f"- Amount MAE: {metrics.get('amount_mae', 0):.2f}\n")
        f.write(f"- Amount RMSE: {metrics.get('amount_rmse', 0):.2f}\n")
        f.write(f"- Max Error: {metrics.get('amount_max_error', 0):.2f}\n")
        f.write(f"- Safety Violations: {metrics.get('safety_violations', 0)}\n")
        f.write(f"- LLM Fallback Rate: {metrics.get('fallback_rate', 0):.1%}\n")
        f.write(f"- Avg LLM Calls: {metrics.get('avg_llm_calls', 0):.2f}\n")
        f.write(f"- p50 Latency: {metrics.get('latency_p50', 0):.2f} ms\n")
        f.write(f"- p95 Latency: {metrics.get('latency_p95', 0):.2f} ms\n")
        f.write(f"- Deterministic Reproducibility: {metrics.get('deterministic_reproducibility', 0):.1%}\n")

    print(f"Benchmark complete. Metrics saved to {metrics_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preds", required=True, type=Path)
    parser.add_argument("--gt", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    
    run_benchmark(args.preds, args.gt, args.out)
