"""
Phase 7: Per-request structured trace logging (observability).

Design principles:
  - Zero coupling to core engine. The tracer is called from benchmark scripts only.
  - No modifications to main.py, cashflow.py, reconciliation.py, or validator.py.
  - Thread-safe: each thread gets its own TraceContext via threading.local().
  - Output: one JSON line per request to evaluation/traces/YYYY-MM-DD/run_<id>.jsonl

Usage:
    from tracer import Tracer

    tracer = Tracer(run_id="phase9_v2", out_dir=Path("evaluation/traces"))
    with tracer.trace(request_id, user_id, mode) as ctx:
        result = process_request(request, store, fx, mode=mode)
        ctx.set_result(result_row)
    # Trace is flushed to disk on __exit__.
"""
from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class LLMCall:
    model: str
    prompt_tokens: int
    response_tokens: int
    latency_ms: float
    fallback: bool
    result_summary: str = ""


@dataclass
class PhaseRecord:
    name: str
    start_ms: float
    end_ms: float

    @property
    def duration_ms(self) -> float:
        return self.end_ms - self.start_ms


@dataclass
class TraceRecord:
    request_id: str
    user_id: str
    mode: str
    run_id: str

    start_time: str = ""
    end_time: str = ""
    latency_ms: float = 0.0

    phases: List[PhaseRecord] = field(default_factory=list)
    llm_calls: List[LLMCall] = field(default_factory=list)
    fallback_triggered: bool = False
    validation_issues: List[str] = field(default_factory=list)
    error: Optional[str] = None

    # Output fields
    amount_safe_to_pay: Optional[str] = None
    affordability_status: Optional[str] = None
    recommended_payment_method: Optional[str] = None
    payment_plan: Optional[str] = None
    earliest_date_for_full_payment: Optional[str] = None
    spending_changes_needed: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "mode": self.mode,
            "run_id": self.run_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "latency_ms": round(self.latency_ms, 3),
            "phases": [
                {"name": p.name, "duration_ms": round(p.duration_ms, 3)}
                for p in self.phases
            ],
            "llm_calls": [
                {
                    "model": c.model,
                    "prompt_tokens": c.prompt_tokens,
                    "response_tokens": c.response_tokens,
                    "latency_ms": round(c.latency_ms, 3),
                    "fallback": c.fallback,
                    "result_summary": c.result_summary,
                }
                for c in self.llm_calls
            ],
            "fallback_triggered": self.fallback_triggered,
            "llm_call_count": len(self.llm_calls),
            "fallback_rate": (
                sum(1 for c in self.llm_calls if c.fallback) / len(self.llm_calls)
                if self.llm_calls else 0.0
            ),
            "validation_issues": self.validation_issues,
            "error": self.error,
            "result": {
                "amount_safe_to_pay": self.amount_safe_to_pay,
                "affordability_status": self.affordability_status,
                "recommended_payment_method": self.recommended_payment_method,
                "payment_plan": self.payment_plan,
                "earliest_date_for_full_payment": self.earliest_date_for_full_payment,
                "spending_changes_needed": self.spending_changes_needed,
            },
        }


# ---------------------------------------------------------------------------
# Thread-local context (allows inner functions to append events without coupling)
# ---------------------------------------------------------------------------

_local = threading.local()


def get_current_trace() -> Optional[TraceRecord]:
    """Return the active TraceRecord for the current thread, or None."""
    return getattr(_local, "trace", None)


def record_llm_call(
    model: str,
    prompt_tokens: int,
    response_tokens: int,
    latency_ms: float,
    fallback: bool,
    result_summary: str = "",
) -> None:
    """
    Append an LLM call record to the current thread's active trace.
    Safe to call even when no trace is active (no-op).
    """
    trace = get_current_trace()
    if trace is None:
        return
    trace.llm_calls.append(LLMCall(
        model=model,
        prompt_tokens=prompt_tokens,
        response_tokens=response_tokens,
        latency_ms=latency_ms,
        fallback=fallback,
        result_summary=result_summary,
    ))
    if fallback:
        trace.fallback_triggered = True


def record_phase(name: str, start_ms: float, end_ms: float) -> None:
    """Append a phase timing record to the current trace."""
    trace = get_current_trace()
    if trace is None:
        return
    trace.phases.append(PhaseRecord(name=name, start_ms=start_ms, end_ms=end_ms))


def add_validation_issue(issue: str) -> None:
    """Record a validation issue in the current trace."""
    trace = get_current_trace()
    if trace is None:
        return
    trace.validation_issues.append(issue)


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TraceContext:
    """Active trace context for a single request."""

    def __init__(self, record: TraceRecord):
        self._record = record

    def set_result(self, row: Dict[str, Any]) -> None:
        r = self._record
        r.amount_safe_to_pay = str(row.get("amount_safe_to_pay", ""))
        r.affordability_status = str(row.get("affordability_status", ""))
        r.recommended_payment_method = str(row.get("recommended_payment_method", ""))
        r.payment_plan = str(row.get("payment_plan", "none"))
        r.earliest_date_for_full_payment = str(row.get("earliest_date_for_full_payment", ""))
        r.spending_changes_needed = str(row.get("spending_changes_needed", "none"))

    def set_error(self, error: str) -> None:
        self._record.error = error

    def add_validation_issues(self, issues: List[str]) -> None:
        self._record.validation_issues.extend(issues)

    @property
    def record(self) -> TraceRecord:
        return self._record


# ---------------------------------------------------------------------------
# Tracer class
# ---------------------------------------------------------------------------

class Tracer:
    """
    Per-request structured trace recorder.

    Thread-safe: uses threading.local() so concurrent benchmark workers don't
    interfere with each other's traces.
    """

    def __init__(self, run_id: str, out_dir: Path):
        self.run_id = run_id
        today = date.today().isoformat()
        self._out_dir = Path(out_dir) / today
        self._out_dir.mkdir(parents=True, exist_ok=True)
        self._out_file = self._out_dir / f"{run_id}.jsonl"
        self._lock = threading.Lock()
        self._records: List[TraceRecord] = []

    @contextmanager
    def trace(
        self,
        request_id: str,
        user_id: str,
        mode: str,
    ) -> Generator[TraceContext, None, None]:
        """
        Context manager for tracing a single request.

        Usage:
            with tracer.trace("req_01", "user_01", "deterministic") as ctx:
                result = process_request(...)
                ctx.set_result(format_result_row(result))
        """
        record = TraceRecord(
            request_id=request_id,
            user_id=user_id,
            mode=mode,
            run_id=self.run_id,
            start_time=datetime.now(timezone.utc).isoformat(),
        )

        # Install in thread-local so inner functions can append events
        _local.trace = record
        t0 = time.perf_counter()

        ctx = TraceContext(record)
        try:
            yield ctx
        except Exception as e:
            record.error = str(e)
            raise
        finally:
            t1 = time.perf_counter()
            record.end_time = datetime.now(timezone.utc).isoformat()
            record.latency_ms = (t1 - t0) * 1000.0

            # Clear thread-local
            _local.trace = None

            # Store record
            with self._lock:
                self._records.append(record)

            # Flush to disk immediately (safe even under concurrent workers)
            self._flush(record)

    def _flush(self, record: TraceRecord) -> None:
        line = json.dumps(record.to_dict(), ensure_ascii=False) + "\n"
        with self._lock:
            with open(self._out_file, "a", encoding="utf-8") as f:
                f.write(line)

    def get_records(self) -> List[TraceRecord]:
        with self._lock:
            return list(self._records)

    def summary(self) -> Dict[str, Any]:
        records = self.get_records()
        if not records:
            return {"count": 0}

        latencies = [r.latency_ms for r in records]
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)

        llm_calls_per_req = [len(r.llm_calls) for r in records]
        fallback_count = sum(1 for r in records if r.fallback_triggered)
        error_count = sum(1 for r in records if r.error)

        return {
            "run_id": self.run_id,
            "total_requests": n,
            "error_count": error_count,
            "latency_ms": {
                "avg": round(sum(latencies) / n, 2),
                "p50": round(latencies_sorted[n // 2], 2),
                "p95": round(latencies_sorted[min(int(n * 0.95), n - 1)], 2),
                "min": round(min(latencies), 2),
                "max": round(max(latencies), 2),
            },
            "llm_calls_per_request": {
                "avg": round(sum(llm_calls_per_req) / n, 2),
                "max": max(llm_calls_per_req),
            },
            "fallback_count": fallback_count,
            "fallback_rate": round(fallback_count / n, 4),
            "output_file": str(self._out_file),
        }

    def save_summary(self, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.summary(), f, indent=2)
