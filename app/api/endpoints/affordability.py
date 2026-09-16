from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.domain import User, FinancialProfile, DecisionRecord, generate_uuid
from app.engine import deterministic_pipeline, AffordabilityRequest
from core.models import UserProfile, PurchaseRequest, BaseEvent
from typing import List, Dict, Any
import time

from app.api.dependencies.auth import get_current_user

router = APIRouter()

@router.post("/check")
def check_affordability(purchase_request: Dict[str, Any], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    start_time = time.time()
    user_id = current_user.user_id
    
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
        
    # Reconstruct core UserProfile
    core_profile = UserProfile(
        user_id=profile.user_id,
        home_currency=profile.home_currency,
        current_available_balance=profile.current_available_balance,
        minimum_balance_to_keep=profile.minimum_balance_to_keep,
        financial_priorities=profile.financial_priorities,
        expense_categories_to_protect=profile.expense_categories_to_protect,
        expense_categories_willing_to_reduce=profile.expense_categories_willing_to_reduce,
        expense_categories_willing_to_stop=profile.expense_categories_willing_to_stop,
        payment_methods_user_will_consider=profile.payment_methods_user_will_consider,
        max_installment_months=profile.max_installment_months
    )
    
    # We construct the PurchaseRequest
    purchase = PurchaseRequest(
        request_id=generate_uuid(),
        user_id=user_id,
        description=purchase_request.get("description", "Purchase"),
        request_amount=purchase_request.get("amount", 0.0),
        currency=purchase_request.get("currency", profile.home_currency),
        request_date=purchase_request.get("date"),
    )
    
    # Generate the request payload for the engine
    req = AffordabilityRequest(
        request_id=purchase.request_id,
        mode="deterministic",
        profile=core_profile,
        transactions=[], # To be pulled from db.events if we had them full, but right now engine uses profile.recurring_incomes
        purchase=purchase
    )
    
    # Execute deterministic pipeline
    try:
        decision_dict = deterministic_pipeline(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    latency = time.time() - start_time
    decision_dict["latency_ms"] = latency * 1000
    
    explanation_data = decision_dict.get("explanation")
    if hasattr(explanation_data, "model_dump"):
        explanation_data = explanation_data.model_dump(mode="json")
    elif hasattr(explanation_data, "dict"):
        explanation_data = explanation_data.dict()
        
    plans_data = decision_dict.get("plans")
    if plans_data:
        plans_data = [p.model_dump(mode="json") if hasattr(p, "model_dump") else p.dict() for p in plans_data]

    # Persist decision
    record = DecisionRecord(
        request_id=purchase.request_id,
        user_id=user_id,
        request_payload=purchase_request,
        status=decision_dict.get("status"),
        explanation=explanation_data,
        plans=plans_data
    )
    db.add(record)
    db.commit()
    
    from app.telemetry import finalize_tracer, get_tracer
    tracer = get_tracer(purchase.request_id)
    tracer.record_stage("[15] DATABASE", "success")
    finalize_tracer(purchase.request_id)
    
    return decision_dict
