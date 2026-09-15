"""
Deterministic final validator.
Validates every output row before writing to output.csv.
Automatically repairs constraint violations using deterministic logic.
"""
from decimal import Decimal
from datetime import date
from typing import List, Optional, Tuple
import logging

from models import DecisionResult, Request, FinancialProfile
from config import (
    AFFORDABLE_NOW, AFFORDABLE_WITH_PLAN, AFFORDABLE_LATER, NOT_AFFORDABLE,
    FULL_PAYMENT, PARTIAL_PAYMENT, INSTALLMENTS, WAIT, NOT_RECOMMENDED
)

logger = logging.getLogger(__name__)
ZERO = Decimal("0")


def validate_and_repair(
    result: DecisionResult,
    request: Request,
    profile: FinancialProfile,
) -> Tuple[DecisionResult, List[str]]:
    """
    Validate a decision result and repair any constraint violations.
    
    Returns:
        (repaired_result, list_of_issues_found)
    """
    issues = []
    
    # 1. Validate amount_safe_to_pay
    if result.amount_safe_to_pay < ZERO:
        issues.append(f"amount_safe_to_pay {result.amount_safe_to_pay} < 0, clamping to 0")
        result.amount_safe_to_pay = ZERO
    
    if result.amount_safe_to_pay > request.requested_amount:
        issues.append(f"amount_safe_to_pay {result.amount_safe_to_pay} > requested {request.requested_amount}, clamping")
        result.amount_safe_to_pay = request.requested_amount
    
    # 2. Validate affordability_status
    valid_statuses = {AFFORDABLE_NOW, AFFORDABLE_WITH_PLAN, AFFORDABLE_LATER, NOT_AFFORDABLE}
    if result.affordability_status not in valid_statuses:
        issues.append(f"Invalid affordability_status: {result.affordability_status}, setting to not_affordable")
        result.affordability_status = NOT_AFFORDABLE
    
    # 3. Validate recommended_payment_method
    valid_methods = {FULL_PAYMENT, PARTIAL_PAYMENT, INSTALLMENTS, WAIT, NOT_RECOMMENDED}
    if result.recommended_payment_method not in valid_methods:
        issues.append(f"Invalid recommended_payment_method: {result.recommended_payment_method}")
        result.recommended_payment_method = NOT_RECOMMENDED
    
    # 4. Validate method is in user's accepted methods (except not_recommended and wait)
    method = result.recommended_payment_method
    user_methods = set(profile.payment_methods_user_will_consider)
    
    if method in (FULL_PAYMENT, PARTIAL_PAYMENT, INSTALLMENTS) and method not in user_methods:
        issues.append(f"Method {method} not in user's accepted methods {user_methods}")
        result.recommended_payment_method = NOT_RECOMMENDED
        result.payment_plan = "none"
        result.affordability_status = NOT_AFFORDABLE
    
    # 5. Validate partial payment constraints
    if method == PARTIAL_PAYMENT:
        if not request.allows_partial_payment:
            issues.append("partial_payment recommended but allows_partial_payment=false")
            result.recommended_payment_method = NOT_RECOMMENDED
            result.payment_plan = "none"
        
        if PARTIAL_PAYMENT not in user_methods:
            issues.append("partial_payment not in user's accepted methods")
            result.recommended_payment_method = NOT_RECOMMENDED
            result.payment_plan = "none"
        
        # Validate exactly 2 payments
        if result.payment_plan and result.payment_plan != "none":
            payments = _parse_payment_plan(result.payment_plan)
            if len(payments) != 2:
                issues.append(f"partial_payment must have exactly 2 payments, has {len(payments)}")
            else:
                total = sum(p[1] for p in payments)
                if abs(total - request.requested_amount) > Decimal("0.05"):
                    issues.append(f"partial payments sum {total} != requested {request.requested_amount}")
    
    # 6. Validate affordable_now requires earliest_date = request_date
    if result.affordability_status == AFFORDABLE_NOW:
        if result.earliest_date_for_full_payment != request.request_date:
            issues.append(f"affordable_now requires earliest_date={request.request_date}, "
                          f"got {result.earliest_date_for_full_payment}")
            result.earliest_date_for_full_payment = request.request_date
    
    # 7. Validate payment plan is chronological
    if result.payment_plan and result.payment_plan != "none":
        payments = _parse_payment_plan(result.payment_plan)
        if payments:
            dates = [p[0] for p in payments]
            if dates != sorted(dates):
                issues.append("payment_plan not in chronological order, sorting")
                payments.sort(key=lambda p: p[0])
                result.payment_plan = _format_payments(payments)
    
    # 8. Validate spending_changes format
    if result.spending_changes_needed and result.spending_changes_needed != "none":
        changes = result.spending_changes_needed.split("|")
        if len(changes) > 3:
            issues.append(f"spending_changes has {len(changes)} items, max 3, truncating")
            result.spending_changes_needed = "|".join(changes[:3])
        
        # Check for duplicate stop/reduce on same event
        event_ids_seen = {}
        valid_changes = []
        for change in changes:
            if change.startswith("stop:"):
                eid = change[5:]
                if eid in event_ids_seen:
                    issues.append(f"Duplicate action on {eid}, removing duplicate")
                    continue
                event_ids_seen[eid] = "stop"
                valid_changes.append(change)
            elif change.startswith("reduce_to:"):
                parts = change.split(":")
                if len(parts) >= 2:
                    eid = parts[1]
                    if eid in event_ids_seen and event_ids_seen[eid] == "stop":
                        issues.append(f"Cannot stop AND reduce {eid}, removing reduce")
                        continue
                    event_ids_seen[eid] = "reduce"
                    valid_changes.append(change)
        
        if len(valid_changes) != len(changes):
            result.spending_changes_needed = "|".join(valid_changes) if valid_changes else "none"
    
    # 9. Ensure not_recommended has no payment plan
    if result.recommended_payment_method == NOT_RECOMMENDED:
        if result.payment_plan and result.payment_plan != "none":
            issues.append("not_recommended should have payment_plan=none")
            result.payment_plan = "none"
    
    # 10. Validate explanation is not empty
    if not result.decision_explanation or len(result.decision_explanation.strip()) < 5:
        result.decision_explanation = _generate_fallback_explanation(result, request, profile)
    
    return result, issues


def _parse_payment_plan(plan_str: str) -> List[Tuple[date, Decimal]]:
    """Parse payment plan string into list of (date, amount) tuples."""
    if not plan_str or plan_str == "none":
        return []
    
    payments = []
    for part in plan_str.split("|"):
        part = part.strip()
        if ":" in part:
            date_str, amount_str = part.rsplit(":", 1)
            try:
                d = date.fromisoformat(date_str.strip())
                a = Decimal(amount_str.strip())
                payments.append((d, a))
            except Exception as e:
                logger.warning(f"Failed to parse payment plan part '{part}': {e}")
    
    return payments


def _format_payments(payments: List[Tuple[date, Decimal]]) -> str:
    """Format payments as payment plan string."""
    parts = []
    for d, a in payments:
        if a == a.to_integral_value():
            amount_str = str(int(a))
        else:
            amount_str = str(a.quantize(Decimal("0.01")))
        parts.append(f"{d.strftime('%Y-%m-%d')}:{amount_str}")
    return "|".join(parts)


def _generate_fallback_explanation(
    result: DecisionResult,
    request: Request,
    profile: FinancialProfile,
) -> str:
    """Generate minimal fallback explanation."""
    currency = profile.home_currency
    method = result.recommended_payment_method
    
    if method == NOT_RECOMMENDED:
        return (f"Do not make this payment by {request.desired_completion_date}. "
                f"None of the available options keeps the {currency} "
                f"{profile.minimum_balance_to_keep} minimum protected.")
    
    if method == WAIT:
        date_str = result.earliest_date_for_full_payment or request.desired_completion_date
        return (f"Pay {currency} {request.requested_amount} in full on {date_str}. "
                f"Paying earlier would put the minimum balance at risk.")
    
    if method == FULL_PAYMENT:
        return (f"Pay {currency} {request.requested_amount} today. "
                f"This keeps the balance above {currency} {profile.minimum_balance_to_keep}.")
    
    return (f"Based on your financial profile, {currency} {result.amount_safe_to_pay} "
            f"can be safely committed using {method}.")
