from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    user_id: str
    home_currency: str = "USD"
    current_available_balance: Optional[Decimal] = None
    minimum_balance_to_keep: Decimal = Field(default=Decimal("0.0"))
    financial_priorities: List[str] = []
    expense_categories_to_protect: List[str] = []
    expense_categories_willing_to_reduce: List[str] = []
    expense_categories_willing_to_stop: List[str] = []
    payment_methods_user_will_consider: List[str] = []
    max_installment_months: Optional[int] = None

class Account(BaseModel):
    account_id: str
    user_id: str
    institution_name: str
    account_type: str

class Balance(BaseModel):
    account_id: str
    available_balance: Decimal
    currency: str
    as_of_date: datetime

class BaseEvent(BaseModel):
    event_id: str
    user_id: str
    description: str
    category: str
    amount: Optional[Decimal]
    currency: str = "USD"
    event_date: date
    settlement_date: Optional[date] = None
    status: str # initiated, pending, confirmed, settled, cancelled, failed, amended, duplicate
    linked_event_id: Optional[str] = None
    event_type: str = "expense" # income, expense

class IncomeEvent(BaseEvent):
    event_type: str = "income"
    source: str
    is_salary: bool = False

class ExpenseEvent(BaseEvent):
    event_type: str = "expense"
    flexibility: str = "fixed" # fixed, stoppable, reducible
    minimum_allowed_amount: Optional[Decimal] = None

class RecurringPattern(BaseModel):
    user_id: str
    category: str
    direction: str # credit or debit
    average_amount: Decimal
    currency: str = "USD"
    frequency_days: int
    typical_day_of_month: Optional[int] = None
    last_date: date
    next_expected_date: date
    confidence: float = 1.0

class RecurringExpense(RecurringPattern):
    direction: str = "debit"
    flexibility: str = "fixed"
    minimum_allowed_amount: Optional[Decimal] = None

class RecurringIncome(RecurringPattern):
    direction: str = "credit"
    is_salary: bool = False
    source: str = "unknown"

class FinancialObligation(BaseModel):
    obligation_id: str
    user_id: str
    description: str
    amount_due: Decimal
    due_date: date
    is_paid: bool = False

class PaymentOption(BaseModel):
    option_id: str
    method: str
    total_months: int
    monthly_payment: Decimal
    total_cost: Decimal
    upfront_payment: Decimal = Decimal("0.0")

class EvidenceFact(BaseModel):
    fact_type: str
    value: Any
    currency: Optional[str] = None
    effective_date: Optional[date] = None
    source_id: str
    confidence: float
    status: str

class EvidenceItem(BaseModel):
    evidence_id: str
    user_id: str
    item_type: str # text, image, document
    raw_content: str
    extracted_facts: List[EvidenceFact] = []

class PurchaseRequest(BaseModel):
    request_id: str
    user_id: str
    description: str
    request_amount: Decimal
    currency: str = "USD"
    request_date: date
    evidence: List[EvidenceItem] = []

class ForecastDay(BaseModel):
    date: date
    opening_balance: Decimal
    credits: Decimal
    debits: Decimal
    closing_balance: Decimal
    minimum_required: Decimal
    is_breached: bool

class RiskFlag(BaseModel):
    risk_type: str
    severity: str
    description: str

class CandidatePlan(BaseModel):
    plan_id: str
    method: str
    amount_today: Decimal
    schedule: List[Dict[str, Any]]
    lowest_projected_balance: Decimal
    limiting_date: date
    safety_margin: Decimal
    is_safe: bool
    risk_flags: List[RiskFlag] = []

class DecisionExplanation(BaseModel):
    summary: str
    safe_amount_today: Decimal
    recommended_plan_id: Optional[str] = None
    lowest_projected_balance: Decimal
    limiting_date: date
    safety_margin: Decimal
    risks: List[str] = []

class Decision(BaseModel):
    request_id: str
    status: str # affordable_now, affordable_with_plan, wait, not_affordable
    explanation: DecisionExplanation
    plans: List[CandidatePlan]
    latency_ms: float
