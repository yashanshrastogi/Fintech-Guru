from decimal import Decimal
from typing import List, Dict, Optional, Any
from datetime import date
from pydantic import BaseModel, Field
from core.models import BaseEvent, RecurringExpense, RecurringIncome, EvidenceFact

class FinancialState(BaseModel):
    """
    Unified representation of the exact financial state.
    Contains strictly reconciled events, projected recurring patterns, 
    and any evidence-based overrides (salary changes, cancellations).
    This serves as the single source of truth for the forecasting engine.
    """
    user_id: str
    request_date: date
    home_currency: str
    current_available_balance: Decimal
    minimum_balance_to_keep: Decimal
    
    # Strictly reconciled one-off events (pending/settled/confirmed)
    reconciled_events: List[BaseEvent] = []
    
    # Projected recurring patterns using statistical forecasting
    recurring_expenses: List[RecurringExpense] = []
    recurring_income: List[RecurringIncome] = []
    
    # Overrides derived from LLM evidence extraction
    evidence_overrides: Dict[str, Any] = {}
    
    def get_effective_salary(self) -> Optional[Decimal]:
        """Returns the salary after applying any evidence-based overrides."""
        if "extracted_salary" in self.evidence_overrides and self.evidence_overrides["extracted_salary"] is not None:
            return Decimal(str(self.evidence_overrides["extracted_salary"]))
        
        # Fallback to the original recurring income pattern for salary
        for inc in self.recurring_income:
            if inc.is_salary:
                return inc.average_amount
        return None
    
    def is_event_cancelled(self, event_id: str) -> bool:
        """Checks if evidence extraction proved the user cancelled an event."""
        if self.evidence_overrides.get("cancellation_request"):
            cancelled_list = self.evidence_overrides.get("cancelled_categories", [])
            for c in cancelled_list:
                if c.lower() in event_id.lower():
                    return True
        return False
