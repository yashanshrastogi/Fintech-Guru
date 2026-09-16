from sqlalchemy import Column, String, Float, Integer, Boolean, Date, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    profile = relationship("FinancialProfile", back_populates="user", uselist=False)
    events = relationship("FinancialEvent", back_populates="user")
    decisions = relationship("DecisionRecord", back_populates="user")
    scenarios = relationship("Scenario", back_populates="user")

class FinancialProfile(Base):
    __tablename__ = "financial_profiles"
    user_id = Column(String, ForeignKey("users.user_id"), primary_key=True)
    home_currency = Column(String, default="USD")
    current_available_balance = Column(Float, nullable=True)
    minimum_balance_to_keep = Column(Float, default=0.0)
    financial_priorities = Column(JSON, default=list) # list of strings
    expense_categories_to_protect = Column(JSON, default=list)
    expense_categories_willing_to_reduce = Column(JSON, default=list)
    expense_categories_willing_to_stop = Column(JSON, default=list)
    payment_methods_user_will_consider = Column(JSON, default=list)
    max_installment_months = Column(Integer, nullable=True)
    
    recurring_incomes = Column(JSON, default=list) # List of dicts matching RecurringIncome
    recurring_expenses = Column(JSON, default=list) # List of dicts matching RecurringExpense
    obligations = Column(JSON, default=list) # List of dicts matching FinancialObligation

    user = relationship("User", back_populates="profile")

class FinancialEvent(Base):
    __tablename__ = "financial_events"
    event_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    description = Column(String)
    category = Column(String)
    amount = Column(Float, nullable=True)
    currency = Column(String, default="USD")
    event_date = Column(Date)
    settlement_date = Column(Date, nullable=True)
    status = Column(String)
    linked_event_id = Column(String, nullable=True)
    event_type = Column(String) # income/expense
    is_salary = Column(Boolean, default=False)
    source = Column(String, nullable=True) # for income
    flexibility = Column(String, nullable=True) # for expense
    minimum_allowed_amount = Column(Float, nullable=True)
    
    user = relationship("User", back_populates="events")

class DecisionRecord(Base):
    __tablename__ = "decisions"
    decision_id = Column(String, primary_key=True, default=generate_uuid)
    request_id = Column(String, index=True) # The ID of the PurchaseRequest
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    request_payload = Column(JSON) # The original purchase request details
    status = Column(String) # affordable_now, wait, etc
    explanation = Column(JSON) # DecisionExplanation dict
    plans = Column(JSON) # List of CandidatePlan dicts
    evidence_metadata = Column(JSON, default=list) # Summarized evidence used
    scenario_id = Column(String, ForeignKey("scenarios.scenario_id"), nullable=True)
    
    user = relationship("User", back_populates="decisions")
    scenario = relationship("Scenario", back_populates="decisions")

class Scenario(Base):
    """Stores what-if modifications from the base state"""
    __tablename__ = "scenarios"
    scenario_id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    base_decision_id = Column(String, nullable=True) # If derived from a previous decision
    overrides = Column(JSON) # e.g. {"requested_amount": 1000, "salary_change": 500, "waiting_days": 30}
    
    user = relationship("User", back_populates="scenarios")
    decisions = relationship("DecisionRecord", back_populates="scenario")
