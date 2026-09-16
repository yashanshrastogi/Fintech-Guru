from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.domain import User, FinancialProfile, DecisionRecord
from typing import Any, Dict
from pydantic import BaseModel
from typing import List, Optional
from app.api.dependencies.auth import get_current_user

router = APIRouter()

class ProfileUpdatePayload(BaseModel):
    home_currency: str = "USD"
    current_available_balance: float
    minimum_balance_to_keep: float
    recurring_incomes: List[Dict[str, Any]] = []
    recurring_expenses: List[Dict[str, Any]] = []
    obligations: List[Dict[str, Any]] = []

@router.get("/{user_id}")
def get_profile(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this profile")
        
    profile = current_user.profile
    if not profile:
        profile = FinancialProfile(user_id=user_id, current_available_balance=0.0)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
    return {
        "user_id": current_user.user_id,
        "home_currency": profile.home_currency,
        "current_available_balance": profile.current_available_balance,
        "minimum_balance_to_keep": profile.minimum_balance_to_keep,
        "recurring_incomes": profile.recurring_incomes,
        "recurring_expenses": profile.recurring_expenses,
        "obligations": profile.obligations
    }

@router.put("/{user_id}")
def update_profile(user_id: str, payload: ProfileUpdatePayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this profile")
        
    profile = current_user.profile
    if not profile:
        profile = FinancialProfile(user_id=user_id)
        db.add(profile)
    
    profile.home_currency = payload.home_currency
    profile.current_available_balance = payload.current_available_balance
    profile.minimum_balance_to_keep = payload.minimum_balance_to_keep
    profile.recurring_incomes = payload.recurring_incomes
    profile.recurring_expenses = payload.recurring_expenses
    profile.obligations = payload.obligations
    
    db.commit()
    return {"status": "success"}

@router.get("/{user_id}/history")
def get_decision_history(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this history")
    records = db.query(DecisionRecord).filter(DecisionRecord.user_id == user_id).order_by(DecisionRecord.created_at.desc()).all()
    
    return {
        "history": [{
            "request_id": r.request_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "request_payload": r.request_payload,
            "status": r.status,
            "explanation": r.explanation,
            "plans": r.plans
        } for r in records]
    }
