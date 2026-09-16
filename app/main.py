import logging
import uuid
import time
import json
from typing import List, Optional
from datetime import date
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from core.models import FinancialProfile, RecurringPattern
from core.state import FinancialState
from optimization.engine import find_max_safe_amount
from optimization.planner import generate_payment_plans
from llm.router import route_request

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fintech_guru_api")

app = FastAPI(title="Fintech Guru V2 API", description="Production deterministic financial decision engine.")

# -------------------------------------------------------------------
# Pydantic Models for the API
# -------------------------------------------------------------------

class ApiFinancialProfile(BaseModel):
    current_available_balance: float
    minimum_balance_to_keep: float = 100.0
    max_installment_months: int = 3

class ApiRecurringEvent(BaseModel):
    category: str
    direction: str
    average_amount: float
    frequency_days: int
    next_expected_date: date
    is_salary: bool = False

class EvaluationRequest(BaseModel):
    request_id: Optional[str] = None
    user_id: str
    request_amount: float
    request_date: date
    mode: str = "deterministic"
    profile: ApiFinancialProfile
    recurring_events: List[ApiRecurringEvent] = []

class PaymentPlanInstallment(BaseModel):
    date: date
    amount: float

class EvaluationResponse(BaseModel):
    request_id: str
    status: str
    method: str
    amount: float
    plan: List[PaymentPlanInstallment]
    latency_ms: float
    error: Optional[str] = None

# -------------------------------------------------------------------
# Core Logic Handlers
# -------------------------------------------------------------------

def deterministic_pipeline(req: EvaluationRequest) -> dict:
    """Core deterministic pipeline logic"""
    # 1. Map to domain models
    recurring_expenses = []
    recurring_income = []
    
    for e in req.recurring_events:
        pattern = RecurringPattern(
            user_id=req.user_id, category=e.category, direction=e.direction,
            average_amount=Decimal(str(e.average_amount)), currency="USD",
            frequency_days=e.frequency_days, typical_day_of_month=None,
            flexibility="fixed", minimum_allowed_amount=None, representative_event_id="ex",
            last_date=req.request_date, next_expected_date=e.next_expected_date,
            is_salary=e.is_salary
        )
        if e.direction == "debit":
            recurring_expenses.append(pattern)
        else:
            recurring_income.append(pattern)
            
    state = FinancialState(
        user_id=req.user_id, request_date=req.request_date, home_currency="USD",
        current_available_balance=Decimal(str(req.profile.current_available_balance)),
        minimum_balance_to_keep=Decimal(str(req.profile.minimum_balance_to_keep)),
        recurring_expenses=recurring_expenses,
        recurring_income=recurring_income
    )
    
    req_amt = Decimal(str(req.request_amount))
    max_safe = find_max_safe_amount(state, req_amt)
    
    if max_safe >= req_amt:
        return {
            "status": "affordable_now",
            "method": "full_payment",
            "amount": float(req_amt),
            "plan": [{"date": req.request_date, "amount": float(req_amt)}]
        }
    
    # Try payment plan
    plans = generate_payment_plans(state, req_amt, max_months=req.profile.max_installment_months)
    if plans:
        best_plan = plans[-1]
        plan_amt = float(best_plan["monthly_payment"])
        
        # Construct schedule
        schedule = []
        d = req.request_date
        for _ in range(best_plan["months"]):
            schedule.append({"date": d, "amount": plan_amt})
            d = d.replace(month=d.month+1) if d.month < 12 else d.replace(year=d.year+1, month=1)
            
        return {
            "status": "affordable_with_plan",
            "method": "payment_plan",
            "amount": plan_amt,
            "plan": schedule
        }
        
    return {
        "status": "not_affordable",
        "method": "none",
        "amount": 0.0,
        "plan": []
    }

def multi_agent_fallback_handler(req: EvaluationRequest) -> dict:
    """Mock multi-agent debate that falls back to deterministic pipeline"""
    logger.warning("MULTI-AGENT DEBATE DISABLED: Falling back to deterministic pipeline")
    result = deterministic_pipeline(req)
    result["_meta"] = {"routed_as": req.mode, "executed_as": "deterministic"}
    return result

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

@app.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_request(req: EvaluationRequest):
    req_id = req.request_id or f"req_{uuid.uuid4().hex[:8]}"
    start_time = time.time()
    
    logger.info(f"Received evaluation request: {req_id} for user {req.user_id} in mode {req.mode}")
    
    try:
        # Enforce routing decision
        pipeline_result = route_request(
            mode=req.mode,
            deterministic_handler=deterministic_pipeline,
            multi_agent_handler=multi_agent_fallback_handler,
            req=req
        )
        
        latency = (time.time() - start_time) * 1000
        
        # Phase 22: Observability Audit Log
        audit_log = {
            "timestamp": time.time(),
            "request_id": req_id,
            "user_id": req.user_id,
            "mode": req.mode,
            "decision_status": pipeline_result["status"],
            "decision_method": pipeline_result["method"],
            "decision_amount": pipeline_result["amount"],
            "latency_ms": latency
        }
        
        # Ensure logs directory exists
        import os
        os.makedirs("logs", exist_ok=True)
        with open("logs/audit.jsonl", "a") as f:
            f.write(json.dumps(audit_log) + "\n")
        
        return EvaluationResponse(
            request_id=req_id,
            status=pipeline_result["status"],
            method=pipeline_result["method"],
            amount=pipeline_result["amount"],
            plan=pipeline_result["plan"],
            latency_ms=latency
        )
        
    except ValueError as e:
        logger.error(f"Routing Error for {req_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Internal Server Error for {req_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal processing error occurred.")
