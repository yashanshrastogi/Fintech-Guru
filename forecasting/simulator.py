from datetime import date, timedelta
from decimal import Decimal
from typing import List, Tuple, Dict
from collections import defaultdict

from core.models import CashFlowDay
from core.state import FinancialState
from forecasting.income import project_next_salary_date

FORECAST_DAYS = 90

def simulate_cashflow(state: FinancialState, extra_debits: List[Tuple[date, Decimal]] = None) -> List[CashFlowDay]:
    """
    Simulates a daily cash flow ledger over a 90-day horizon using a unified FinancialState.
    """
    end_date = state.request_date + timedelta(days=FORECAST_DAYS)
    ledger: Dict[date, List[Tuple[Decimal, str, bool]]] = defaultdict(list)
    
    # 1. Apply reconciled one-off events
    for event in state.reconciled_events:
        effective_date = event.settlement_date or event.event_date or state.request_date
        if state.request_date <= effective_date <= end_date:
            amt = event.amount_home_currency or event.amount or Decimal("0")
            is_debit = (event.direction == "debit")
            ledger[effective_date].append((amt, f"event:{event.event_id}", is_debit))
            
    # 2. Apply recurring expenses
    for exp in state.recurring_expenses:
        next_d = exp.next_expected_date
        while next_d <= end_date:
            if next_d >= state.request_date:
                ledger[next_d].append((exp.average_amount, f"recurring_exp:{exp.category}", True))
            next_d += timedelta(days=exp.frequency_days)
            
    # 3. Apply recurring income (Salary)
    for inc in state.recurring_income:
        if inc.is_salary:
            eff_salary = state.get_effective_salary()
            if eff_salary is not None:
                next_d = inc.next_expected_date
                while next_d <= end_date:
                    if next_d >= state.request_date:
                        ledger[next_d].append((eff_salary, f"salary:{inc.category}", False))
                    next_d = project_next_salary_date(next_d, inc.typical_day_of_month or 1, next_d)
                    if not next_d:
                        break
        else:
            next_d = inc.next_expected_date
            while next_d <= end_date:
                if next_d >= state.request_date:
                    ledger[next_d].append((inc.average_amount, f"recurring_inc:{inc.category}", False))
                next_d += timedelta(days=inc.frequency_days)
                
    # 4. Apply extra debits (e.g. proposed payment plans)
    if extra_debits:
        for pay_date, pay_amount in extra_debits:
            if state.request_date <= pay_date <= end_date:
                ledger[pay_date].append((pay_amount, "proposed_payment", True))
                
    # 5. Build daily objects
    balance = state.current_available_balance
    days = []
    
    current_date = state.request_date
    while current_date <= end_date:
        income = Decimal("0")
        expenses = Decimal("0")
        event_refs = []
        
        for amt, ref, is_debit in ledger.get(current_date, []):
            if is_debit:
                expenses += amt
            else:
                income += amt
            event_refs.append(ref)
            
        opening = balance
        balance = opening + income - expenses
        
        days.append(CashFlowDay(
            day=current_date,
            opening_balance=opening,
            income=income,
            expenses=expenses,
            closing_balance=balance,
            events=event_refs
        ))
        
        current_date += timedelta(days=1)
        
    return days
