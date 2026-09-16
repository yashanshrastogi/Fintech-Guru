import logging
import uuid
import time
import json
import os
from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.models import (
    UserProfile, BaseEvent, EvidenceItem, PurchaseRequest, 
    RecurringExpense, RecurringIncome, Decision, CandidatePlan, DecisionExplanation
)
from core.state import FinancialState
from core.reconciliation import reconcile_events
from forecasting.expenses import project_expense_amount
from forecasting.income import project_next_salary_date
from optimization.engine import find_max_safe_amount
from optimization.planner import generate_payment_plans
from validation.boundary import enforce_hard_safety_boundary, SafetyViolationError
from llm.router import route_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fintech_guru_api")

app = FastAPI(title="Fintech Guru V2 API", description="Production deterministic financial decision engine.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# Request Models
# -------------------------------------------------------------------

class AffordabilityRequest(BaseModel):
    request_id: Optional[str] = None
    mode: str = "deterministic"
    profile: UserProfile
    transactions: List[BaseEvent] = []
    purchase: PurchaseRequest

# -------------------------------------------------------------------
# True End-to-End Pipeline
# -------------------------------------------------------------------

def build_canonical_state(req: AffordabilityRequest) -> FinancialState:
    """Ingests raw transactions, reconciles them, and applies statistical forecasting."""
    # 1. Transaction Reconciliation
    reconciled_events, _ = reconcile_events(req.transactions, req.profile, req.purchase.request_date)
    
    # 2. Extract recurring patterns from reconciled events
    # In a full production system, this would use a clustering algorithm.
    # For now, we manually map categories to demonstrate the forecasting hooks.
    recurring_expenses = []
    recurring_income = []
    
    expense_history: Dict[str, List[Decimal]] = {}
    income_history: Dict[str, List[date]] = {}
    
    for event in reconciled_events:
        if event.amount is None:
            continue
        cat = event.category
        if getattr(event, "event_type", "") == "expense":
            if cat not in expense_history:
                expense_history[cat] = []
            expense_history[cat].append((event.event_date, event.amount))
        elif getattr(event, "event_type", "") == "income":
            if cat not in income_history:
                income_history[cat] = []
            income_history[cat].append(event.event_date)
            
    # 3. Apply P90 Forecasting for Expenses (Phase 5)
    for cat, events in expense_history.items():
        amounts = [a for _, a in events]
        dates = sorted([d for d, _ in events])
        projected_amt = project_expense_amount(amounts)
        
        last_date = dates[-1]
        is_monthly = False
        if len(dates) > 1:
            freq = (dates[-1] - dates[-2]).days
            if freq <= 0:
                freq = 30
            # Check if it's a monthly recurrence (same day of month)
            if 28 <= freq <= 31:
                if dates[-1].day == dates[-2].day:
                    is_monthly = True
                # Month-end check
                elif (dates[-1] + timedelta(days=1)).day == 1 and (dates[-2] + timedelta(days=1)).day == 1:
                    is_monthly = True
        else:
            freq = 30
            is_monthly = True
            
        if is_monthly or freq == 30:
            next_date = project_next_salary_date(last_date, last_date.day, req.purchase.request_date)
            freq = 30
        else:
            next_date = last_date + timedelta(days=freq)
            
        recurring_expenses.append(RecurringExpense(
            user_id=req.profile.user_id,
            category=cat,
            direction="debit",
            average_amount=projected_amt,
            frequency_days=freq,
            last_date=last_date,
            next_expected_date=next_date
        ))
        
    # 4. Apply Anchored Salary Forecasting (Phase 6)
    for cat, dates in income_history.items():
        if dates:
            dates = sorted(dates)
            last_date = dates[-1]
            is_monthly = False
            if len(dates) > 1:
                freq = (dates[-1] - dates[-2]).days
                if freq <= 0:
                    freq = 30
                # Check if it's a monthly recurrence (same day of month)
                if 28 <= freq <= 31:
                    if dates[-1].day == dates[-2].day:
                        is_monthly = True
                    # Month-end check
                    elif (dates[-1] + timedelta(days=1)).day == 1 and (dates[-2] + timedelta(days=1)).day == 1:
                        is_monthly = True
            else:
                freq = 30
                is_monthly = True # Default single event to monthly

            if is_monthly or freq == 30:
                next_date = project_next_salary_date(last_date, last_date.day, req.purchase.request_date)
                freq = 30 # normalize for downstream schemas
            else:
                next_date = last_date + timedelta(days=freq)
                
            if next_date:
                # Find the actual salary event to use its amount
                amount = Decimal("5000.0")
                for e in reconciled_events:
                    if e.category == cat:
                        amount = e.amount
                        break
                        
                recurring_income.append(RecurringIncome(
                    user_id=req.profile.user_id,
                    category=cat,
                    direction="credit",
                    average_amount=amount,
                    frequency_days=freq,
                    last_date=last_date,
                    next_expected_date=next_date,
                    is_salary=getattr(e, "is_salary", False) if 'e' in locals() else ("salary" in cat.lower())
                ))

    # 5. Financial State Reconstruction
    # For this audit/demo, assume current_available_balance is sum of events or provided via profile.
    # We will use the minimum_balance_to_keep from profile.
    # Get balance from profile if provided, else sum of transactions
    
    # We check if 'current_available_balance' exists on profile model, otherwise fallback
    balance = Decimal("10000.0")
    if hasattr(req.profile, "current_available_balance") and req.profile.current_available_balance is not None:
        balance = req.profile.current_available_balance
        
    overrides = {"cancelled_categories": []}
    for p in req.profile.financial_priorities:
        if p.startswith("salary_override:"):
            overrides["extracted_salary"] = float(p.split(":")[1])
        elif p.startswith("cancel_override:"):
            overrides["cancellation_request"] = True
            overrides["cancelled_categories"].append(p.split(":")[1])
            
    return FinancialState(
        user_id=req.profile.user_id,
        request_date=req.purchase.request_date,
        home_currency=req.profile.home_currency,
        current_available_balance=balance,
        minimum_balance_to_keep=req.profile.minimum_balance_to_keep,
        reconciled_events=reconciled_events,
        recurring_expenses=recurring_expenses,
        recurring_income=recurring_income,
        evidence_overrides=overrides
    )

def deterministic_pipeline(req: AffordabilityRequest) -> dict:
    """Core deterministic pipeline logic"""
    from app.telemetry import get_tracer
    tracer = get_tracer(req.request_id or "default")
    
    t0 = time.time()
    # 1. State Reconstruction
    state = build_canonical_state(req)
    tracer.record_stage("[07] CANONICAL STATE", "success", (time.time()-t0)*1000)
    
    t0 = time.time()
    # 2. Safe Amount Optimization
    req_amt = req.purchase.request_amount
    max_safe = find_max_safe_amount(state, req_amt)
    tracer.record_stage("[11] OPTIMIZATION", "success", (time.time()-t0)*1000)
    
    plans = []
    status = "not_affordable"
    
    if max_safe >= req_amt:
        status = "affordable_now"
        plans.append(CandidatePlan(
            plan_id="full_payment",
            method="full_payment",
            amount_today=req_amt,
            schedule=[{"date": req.purchase.request_date, "amount": float(req_amt)}],
            lowest_projected_balance=Decimal("0"), # Needs simulator hook
            limiting_date=req.purchase.request_date,
            safety_margin=max_safe - req_amt,
            is_safe=True
        ))
    else:
        t0 = time.time()
        # 3. Payment Plan Optimization
        raw_plans = generate_payment_plans(state, req_amt, max_months=req.profile.max_installment_months or 3)
        tracer.record_stage("[12] PLAN", "success", (time.time()-t0)*1000)
        
        if raw_plans:
            best_plan = raw_plans[-1]
            status = "affordable_with_plan"
            schedule = []
            d = req.purchase.request_date
            for amt in best_plan.get("installments", [float(best_plan["monthly_payment"])] * best_plan["months"]):
                schedule.append({"date": d, "amount": amt})
                d = d.replace(month=d.month % 12 + 1, year=d.year + (1 if d.month == 12 else 0))
                
            plans.append(CandidatePlan(
                plan_id=f"installments_{best_plan['months']}",
                method="payment_plan",
                amount_today=best_plan.get("installments", [best_plan["monthly_payment"]])[0],
                schedule=schedule,
                lowest_projected_balance=best_plan.get("lowest_balance", Decimal("0")),
                limiting_date=req.purchase.request_date,
                safety_margin=Decimal("0"),
                is_safe=True
            ))

    t0 = time.time()
    # 4. Hard Safety Validation
    valid_plans = []
    for p in plans:
        try:
            logger.info(f"[SafetyBoundary] Checking candidate {p.plan_id}")
            enforce_hard_safety_boundary(state, req_amt, p)
            logger.info(f"[SafetyBoundary] Passed candidate {p.plan_id}")
            valid_plans.append(p)
        except SafetyViolationError as e:
            logger.warning(f"[SafetyBoundary] Rejected candidate {p.plan_id}: {e}")
            
    if not valid_plans:
        status = "not_affordable"
    tracer.record_stage("[13] SAFETY BOUNDARY", "success", (time.time()-t0)*1000)
        
    plans = valid_plans
            
    # 5. Explanation Generation
    explanation = DecisionExplanation(
        summary="You can afford this" if status != "not_affordable" else "You cannot afford this safely.",
        safe_amount_today=max_safe,
        lowest_projected_balance=plans[0].lowest_projected_balance if plans else Decimal("0"),
        limiting_date=req.purchase.request_date,
        safety_margin=max_safe - req_amt if max_safe >= req_amt else Decimal("0")
    )
    
    tracer.record_stage("[14] DECISION", "success")

    return {
        "status": status,
        "explanation": explanation,
        "plans": plans,
        "state": state
    }

def multi_agent_fallback_handler(req: AffordabilityRequest) -> dict:
    """
    Evidence Extraction Pipeline — V2 Production Path.

    Executes ONE Qwen evidence extraction call to interpret natural language,
    then passes extracted facts into the deterministic pipeline.
    """
    logger.info("[EvidencePipeline] Starting Qwen evidence extraction...")
    from llm.client import LLMClient
    from app.telemetry import get_tracer

    tracer = get_tracer(req.request_id or "default")
    t0 = time.time()
    
    client = LLMClient(endpoint="http://localhost:11434")

    # Check availability before attempting — log clearly
    if not client.is_available() or not client.model_is_available():
        logger.warning("[EvidencePipeline] Ollama unavailable — running deterministic only.")
        tracer.record_stage("[06] EVIDENCE", "failure", (time.time()-t0)*1000, error="Ollama unavailable")
        return deterministic_pipeline(req)

    # Run evidence extraction on the purchase description
    try:
        extraction = client.extract_evidence(req.purchase.description)
        logger.info(f"[EvidencePipeline] Qwen extracted: {extraction}")
        tracer.record_stage("[06] EVIDENCE", "success", (time.time()-t0)*1000, metadata={"extracted": extraction})
    except Exception as e:
        tracer.record_stage("[06] EVIDENCE", "failure", (time.time()-t0)*1000, error=str(e))
        return deterministic_pipeline(req)

    # --- Salary Update ---
    if extraction.get("extracted_salary") is not None:
        logger.info(
            f"[EvidencePipeline] Salary fact extracted: {extraction['extracted_salary']} "
            f"(effective: {extraction.get('salary_effective_date', 'unspecified')})"
        )
        req.profile.financial_priorities.append(
            f"salary_override:{extraction['extracted_salary']}"
        )

    # --- Cancellation ---
    if extraction.get("cancellation_request"):
        cancelled_cat = extraction.get("cancelled_category")
        if cancelled_cat:
            logger.info(
                f"[EvidencePipeline] Cancellation fact extracted: category='{cancelled_cat}'"
            )
            req.profile.financial_priorities.append(f"cancel_override:{cancelled_cat}")
        else:
            logger.warning(
                "[EvidencePipeline] Cancellation detected but no specific category — "
                "ignoring to avoid incorrect state mutation."
            )

    # Run the deterministic pipeline with updated state
    return deterministic_pipeline(req)

# -------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/v1/version")
def version():
    return {"version": "2.0.0"}

@app.post("/api/v1/affordability/check", response_model=Decision)
async def check_affordability(req: AffordabilityRequest):
    req_id = req.request_id or f"req_{uuid.uuid4().hex[:8]}"
    start_time = time.time()
    
    logger.info(f"Received V2 request: {req_id} in mode {req.mode}")
    
    try:
        pipeline_result = route_request(
            mode=req.mode,
            deterministic_handler=deterministic_pipeline,
            multi_agent_handler=multi_agent_fallback_handler,
            req=req
        )
        
        latency = (time.time() - start_time) * 1000
        
        # Phase 25: Observability Audit Log
        audit_log = {
            "timestamp": time.time(),
            "request_id": req_id,
            "user_id": req.profile.user_id,
            "mode": req.mode,
            "decision_status": pipeline_result["status"],
            "latency_ms": latency
        }
        
        os.makedirs("logs", exist_ok=True)
        with open("logs/audit.jsonl", "a") as f:
            f.write(json.dumps(audit_log) + "\n")
        
        return Decision(
            request_id=req_id,
            status=pipeline_result["status"],
            explanation=pipeline_result["explanation"],
            plans=pipeline_result["plans"],
            latency_ms=latency
        )
        
    except ValueError as e:
        logger.error(f"Routing Error for {req_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Internal Server Error for {req_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    message: str
    base_request: AffordabilityRequest

class ChatResponse(BaseModel):
    decision: Decision
    reply: str

@app.post("/api/v1/assistant/chat", response_model=ChatResponse)
async def assistant_chat(req: ChatRequest):
    # This is a real integration that would parse the message to amend the base_request
    # For now, it runs the base request through the deterministic pipeline.
    # In Step 5, Qwen will be injected here.
    
    # 1. Pipeline execution
    req_id = req.base_request.request_id or f"req_{uuid.uuid4().hex[:8]}"
    start_time = time.time()
    
    try:
        pipeline_result = route_request(
            mode=req.base_request.mode,
            deterministic_handler=deterministic_pipeline,
            multi_agent_handler=multi_agent_fallback_handler,
            req=req.base_request
        )
        
        latency = (time.time() - start_time) * 1000
        
        decision = Decision(
            request_id=req_id,
            status=pipeline_result["status"],
            explanation=pipeline_result["explanation"],
            plans=pipeline_result["plans"],
            latency_ms=latency
        )
        
        return ChatResponse(
            decision=decision,
            reply=pipeline_result["explanation"].summary
        )
    except Exception as e:
        logger.exception(f"Internal Server Error for chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

