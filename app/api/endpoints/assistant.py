from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.domain import FinancialProfile, User, generate_uuid, DecisionRecord
from app.engine import deterministic_pipeline, AffordabilityRequest
from core.models import UserProfile, PurchaseRequest
from llm.client import LLMClient
from pydantic import BaseModel
from typing import Any, Dict
import time
import os

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

from app.api.dependencies.auth import get_current_user
from app.config import settings

@router.post("/chat")
def handle_chat(payload: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    start_time = time.time()
    
    profile = current_user.profile
    # We don't raise 404 immediately; we route intents first.

    # 1. Use Qwen to extract intent and entities from the chat message
    client = LLMClient(endpoint=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
    intent_data = client.analyze_message(payload.message)
    intent = intent_data.get("intent", "UNSUPPORTED")
    reply = intent_data.get("reply", "I'm not sure how to handle that.")

    if intent in ["GREETING", "GENERAL", "UNSUPPORTED"]:
        return {"reply": reply, "intent": intent, "decision": None, "extracted_evidence": intent_data}

    if intent == "PROFILE_UPDATE":
        prof_data = intent_data.get("profile_data", {})
        if prof_data:
            if not profile:
                profile = FinancialProfile(user_id=current_user.user_id)
                db.add(profile)
            if prof_data.get("balance") is not None:
                profile.current_available_balance = float(prof_data["balance"])
            if prof_data.get("reserve") is not None:
                profile.minimum_balance_to_keep = float(prof_data["reserve"])
            # Assuming simple income/expense mapping for demonstration, robust app would map to recurring arrays
            if prof_data.get("income") is not None:
                profile.recurring_incomes = [{"category": "salary", "direction": "credit", "average_amount": float(prof_data["income"]), "frequency_days": 30, "is_salary": True}]
            if prof_data.get("expenses") is not None:
                profile.recurring_expenses = [{"category": "expenses", "direction": "debit", "average_amount": float(prof_data["expenses"]), "frequency_days": 30}]
            db.commit()
            
            # Re-fetch profile to ensure it's loaded
            db.refresh(profile)

        return {"reply": reply, "intent": intent, "decision": None, "extracted_evidence": intent_data}

    if intent == "HISTORY":
        return {"reply": "You can view your history on the dashboard.", "intent": intent, "decision": None, "extracted_evidence": intent_data}

    # If the intent requires the engine, we MUST have a profile
    if not profile:
        return {"reply": "Please set up your financial profile first (current balance, minimum reserve, income, expenses) before asking about affordability.", "intent": "UNSUPPORTED", "decision": None, "extracted_evidence": intent_data}

    # 2. Extract or Recover Context for Engine
    import datetime
    request_date = datetime.date.today()
    amount = intent_data.get("amount")
    description = intent_data.get("description", payload.message)

    if intent == "EXPLANATION" or intent == "WHAT_IF":
        last_decision = db.query(DecisionRecord).filter(DecisionRecord.user_id == current_user.user_id).order_by(DecisionRecord.created_at.desc()).first()
        if not last_decision:
            return {"reply": "I don't see a recent purchase query to modify or explain.", "intent": intent, "decision": None, "extracted_evidence": intent_data}
        
        if intent == "EXPLANATION":
            exp = last_decision.explanation.get("summary", "No explanation available.") if isinstance(last_decision.explanation, dict) else str(last_decision.explanation)
            return {"reply": exp, "intent": intent, "decision": None, "extracted_evidence": intent_data}

        # Recover amount/description from last decision
        amount = last_decision.request_payload.get("amount", amount)
        description = last_decision.request_payload.get("description", description)

        # Apply overrides
        overrides = intent_data.get("overrides", {})
        if overrides.get("waiting_days"):
            request_date = request_date + datetime.timedelta(days=int(overrides["waiting_days"]))
        if overrides.get("payment_now"):
            # A bit of a hack to reduce the purchase amount if they pay some now, or change the logic
            # For strict what-if, we just pass it to the engine. The engine doesn't have a direct "payment_now" override yet, 
            # so we'll just evaluate the remaining amount for simplicity if they pay it down.
            pass 

    if not amount or amount <= 0:
        import re
        amount_match = re.search(r'\$?(\d+(\.\d+)?)', payload.message)
        amount = float(amount_match.group(1)) if amount_match else 0.0

    if amount <= 0:
        return {"reply": "Please specify an amount for the purchase.", "intent": intent, "decision": None, "extracted_evidence": intent_data}

    # 3. Build State
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

    purchase = PurchaseRequest(
        request_id=generate_uuid(),
        user_id=current_user.user_id,
        description=description or payload.message,
        request_amount=amount,
        currency=profile.home_currency,
        request_date=request_date.isoformat()
    )

    req = AffordabilityRequest(
        request_id=purchase.request_id,
        mode="agentic",
        profile=core_profile,
        transactions=[], 
        purchase=purchase
    )

    from core.models import BaseEvent, IncomeEvent
    sim_events = []
    for inc in profile.recurring_incomes:
        sim_events.append(BaseEvent(
            event_id=generate_uuid(),
            user_id=profile.user_id,
            description=f"Recent {inc.get('category')}",
            category=inc.get("category", "Income"),
            amount=inc.get("average_amount", 0.0),
            event_date=(datetime.date.today() - datetime.timedelta(days=inc.get("frequency_days", 30))).isoformat(),
            status="settled",
            event_type="income",
            is_salary=inc.get("is_salary", False)
        ))
    for exp in profile.recurring_expenses:
        sim_events.append(BaseEvent(
            event_id=generate_uuid(),
            user_id=profile.user_id,
            description=f"Recent {exp.get('category')}",
            category=exp.get("category", "Expense"),
            amount=exp.get("average_amount", 0.0),
            event_date=(datetime.date.today() - datetime.timedelta(days=exp.get("frequency_days", 30))).isoformat(),
            status="settled",
            event_type="expense"
        ))
    
    # If WHAT_IF has salary_change override, mutate the sim_events before running
    if intent == "WHAT_IF" and "salary_change" in intent_data.get("overrides", {}):
        salary_diff = float(intent_data["overrides"]["salary_change"])
        for ev in sim_events:
            if ev.is_salary:
                ev.amount += salary_diff

    req.transactions = sim_events

    # 4. Run Pipeline
    try:
        from llm.router import route_request
        from app.engine import multi_agent_fallback_handler
        pipeline_result = route_request(
            mode=req.mode,
            deterministic_handler=deterministic_pipeline,
            multi_agent_handler=multi_agent_fallback_handler,
            req=req
        )
        decision_dict = pipeline_result
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

    # Save ONLY if it's an affordability query or what if
    record = DecisionRecord(
        request_id=purchase.request_id,
        user_id=current_user.user_id,
        request_payload={"message": payload.message, "intent": intent, "amount": amount, "description": description},
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

    reply_str = reply if intent == "WHAT_IF" and reply else (explanation_data.get("summary", "Analysis complete.") if isinstance(explanation_data, dict) else "Analysis complete.")

    return {
        "reply": reply_str,
        "intent": intent,
        "decision": {
            "status": decision_dict.get("status"),
            "explanation": explanation_data,
            "plans": plans_data
        },
        "extracted_evidence": intent_data
    }
