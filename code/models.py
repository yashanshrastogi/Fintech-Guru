"""
Data models for the Buy or Wait? financial decision agent.
Uses Decimal for all monetary amounts to avoid floating-point rounding errors.
"""
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Optional, List, Dict, Any


def to_decimal(value) -> Decimal:
    """Convert a value to Decimal safely."""
    if value is None or value == "" or (isinstance(value, float) and not value == value):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


@dataclass
class FinancialProfile:
    user_id: str
    home_currency: str
    current_available_balance: Decimal
    minimum_balance_to_keep: Decimal
    financial_priorities: List[str]          # e.g. ["education", "debt_repayment"]
    expense_categories_to_protect: List[str]  # e.g. ["rent", "groceries"]
    expense_categories_willing_to_reduce: List[str]
    expense_categories_willing_to_stop: List[str]
    payment_methods_user_will_consider: List[str]  # e.g. ["full_payment", "installments"]
    max_installment_months: Optional[int]


@dataclass
class FinancialEvent:
    event_id: str
    user_id: str
    event_type: str          # expense, income, subscription, debt_payment, investment, refund
    description: str
    category: str
    direction: str           # debit or credit
    amount: Optional[Decimal]  # May be blank — must be recovered from image
    currency: str
    event_date: date
    settlement_date: Optional[date]
    status: str              # settled, pending, scheduled, cancelled, failed, confirmed
    linked_event_id: Optional[str]
    flexibility: str         # fixed, stoppable, reducible, reducible_or_stoppable
    minimum_allowed_amount: Optional[Decimal]
    
    # Derived fields
    amount_home_currency: Optional[Decimal] = None
    is_recurring: bool = False
    recurrence_period_days: Optional[int] = None


@dataclass
class RecurringPattern:
    """A detected recurring expense or income pattern."""
    user_id: str
    category: str
    direction: str
    average_amount: Decimal
    currency: str
    frequency_days: int          # Approximate days between occurrences
    typical_day_of_month: Optional[int]
    flexibility: str
    minimum_allowed_amount: Optional[Decimal]
    representative_event_id: str  # Last known event_id for this pattern
    last_date: date
    next_expected_date: date
    is_salary: bool = False


@dataclass
class PaymentOption:
    payment_option_id: str
    request_id: str
    payment_method: str        # full_payment, installments
    payment_amount: Decimal    # Per-payment amount
    number_of_payments: int
    first_payment_date: date
    payment_frequency_days: Optional[int]  # Days between payments (None for full_payment)
    financing_fee: Decimal
    total_payable_amount: Decimal


@dataclass
class Request:
    request_id: str
    user_id: str
    request_date: date
    request_type: str
    requested_amount: Decimal
    desired_completion_date: date
    allows_partial_payment: bool
    request_text: str


@dataclass
class MessageEvidence:
    message_id: str
    user_id: str
    request_id: Optional[str]
    related_event_id: Optional[str]
    sent_at: str
    source_type: str
    message_text: str
    
    # Parsed fields
    parsed_intent: Optional[str] = None  # salary_change, cancel, delay, confirm, etc.
    parsed_amount: Optional[Decimal] = None
    parsed_currency: Optional[str] = None
    parsed_date: Optional[date] = None
    confidence: float = 0.0


@dataclass
class ImageEvidence:
    image_id: str
    user_id: str
    request_id: Optional[str]
    related_event_id: Optional[str]
    
    # Extracted fields
    extracted_amount: Optional[Decimal] = None
    extracted_currency: Optional[str] = None
    extracted_date: Optional[date] = None
    confidence: float = 0.0
    raw_text: Optional[str] = None


@dataclass
class CashFlowDay:
    """Represents the financial state on a specific day."""
    day: date
    opening_balance: Decimal
    income: Decimal = Decimal("0")
    expenses: Decimal = Decimal("0")
    closing_balance: Decimal = Decimal("0")
    events: List[str] = field(default_factory=list)  # event_ids on this day


@dataclass
class CandidatePlan:
    """A candidate payment plan to evaluate."""
    candidate_id: str
    payment_method: str          # full_payment, partial_payment, installments, wait, not_recommended
    payment_option_id: Optional[str]  # For installment options
    payment_schedule: List[tuple]    # List of (date, amount)
    total_amount_paid: Decimal
    completion_date: Optional[date]
    spending_changes: List[str]   # ["stop:event_id", "reduce_to:event_id:amount"]
    minimum_forecast_balance: Decimal
    deadline_met: bool
    user_preference_allowed: bool
    safety_status: str           # safe, unsafe
    reason_codes: List[str]
    
    # Ranking fields
    requires_spending_changes: bool = False
    num_payments: int = 1
    starts_on_request_date: bool = True


@dataclass
class DecisionResult:
    """Final output for a single request."""
    request_id: str
    amount_safe_to_pay: Decimal
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str            # Formatted as "YYYY-MM-DD:amount|..."
    earliest_date_for_full_payment: Optional[date]
    spending_changes_needed: str  # Formatted as "stop:X|reduce_to:Y:Z" or "none"
    decision_explanation: str


@dataclass
class UsageRecord:
    """Track LLM API usage for cost reporting."""
    provider: str
    model: str
    request_id: str
    agent: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    estimated_cost_usd: float
