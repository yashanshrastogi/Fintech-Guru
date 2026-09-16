from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.domain import User, FinancialProfile, DecisionRecord, Scenario, generate_uuid
from app.engine import deterministic_pipeline, AffordabilityRequest
from core.models import UserProfile, PurchaseRequest
from typing import List, Dict, Any
import time

router = APIRouter()

from pydantic import BaseModel
from typing import Optional

class WhatIfOverrides(BaseModel):
    requested_amount: float
    request_date: str
    salary_change: Optional[float] = None
    cancel_expense: Optional[str] = None
    installment_months: Optional[int] = None

@router.post("/")
def evaluate_scenario(user_id: str, overrides: WhatIfOverrides, db: Session = Depends(get_db)):
    # 1. Fetch base profile
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
        
    # 2. Clone and apply overrides
    # e.g., overrides = {"salary_change": 500, "cancel_expense": "Netflix", "requested_amount": 1200}
    
    cloned_priorities = list(profile.financial_priorities)
    if overrides.salary_change is not None:
        # Assuming current salary is stored, we add override to priorities
        cloned_priorities.append(f"salary_override:{overrides.salary_change}")
    if overrides.cancel_expense is not None:
        cloned_priorities.append(f"cancel_override:{overrides.cancel_expense}")
        
    core_profile = UserProfile(
        user_id=profile.user_id,
        home_currency=profile.home_currency,
        current_available_balance=profile.current_available_balance,
        minimum_balance_to_keep=profile.minimum_balance_to_keep,
        financial_priorities=cloned_priorities,
        expense_categories_to_protect=profile.expense_categories_to_protect,
        expense_categories_willing_to_reduce=profile.expense_categories_willing_to_reduce,
        expense_categories_willing_to_stop=profile.expense_categories_willing_to_stop,
        payment_methods_user_will_consider=profile.payment_methods_user_will_consider,
        max_installment_months=overrides.installment_months or profile.max_installment_months
    )
    
    purchase = PurchaseRequest(
        request_id=generate_uuid(),
        user_id=user_id,
        description="What-If Purchase",
        request_amount=overrides.requested_amount,
        currency=profile.home_currency,
        request_date=overrides.request_date,
    )
    
    req = AffordabilityRequest(
        request_id=purchase.request_id,
        mode="deterministic",
        profile=core_profile,
        transactions=[], 
        purchase=purchase
    )
    
    # 3. Save the Scenario
    scenario = Scenario(
        user_id=user_id,
        overrides=overrides
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    
    # 4. Evaluate
    try:
        decision_dict = deterministic_pipeline(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    explanation_data = decision_dict.get("explanation")
    if hasattr(explanation_data, "model_dump"):
        explanation_data = explanation_data.model_dump(mode="json")
    elif hasattr(explanation_data, "dict"):
        explanation_data = explanation_data.dict()
        
    plans_data = decision_dict.get("plans")
    if plans_data:
        plans_data = [p.model_dump(mode="json") if hasattr(p, "model_dump") else p.dict() for p in plans_data]

    # 5. Save transient decision
    record = DecisionRecord(
        request_id=purchase.request_id,
        user_id=user_id,
        request_payload=overrides,
        status=decision_dict.get("status"),
        explanation=explanation_data,
        plans=plans_data,
        scenario_id=scenario.scenario_id
    )
    db.add(record)
    db.commit()
    
    return decision_dict
