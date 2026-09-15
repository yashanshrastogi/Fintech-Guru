"""
Candidate plan generation and ranking.
Generates all possible payment plans and ranks them per the problem spec.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from typing import List, Optional, Dict, Tuple
import logging

from models import (
    FinancialProfile, FinancialEvent, PaymentOption, CandidatePlan, Request
)
from cashflow import (
    simulate_cashflow, is_plan_safe, get_minimum_balance_in_period,
    find_earliest_full_payment_date, simulate_installment_plan,
    _build_payment_schedule, find_amount_safe_to_pay
)
from config import (
    FULL_PAYMENT, PARTIAL_PAYMENT, INSTALLMENTS, WAIT, NOT_RECOMMENDED,
    AFFORDABLE_NOW, AFFORDABLE_WITH_PLAN, AFFORDABLE_LATER, NOT_AFFORDABLE,
    FORECAST_DAYS
)

logger = logging.getLogger(__name__)
ZERO = Decimal("0")


def generate_candidates(
    request: Request,
    profile: FinancialProfile,
    events: List[FinancialEvent],
    patterns: List[dict],
    payment_options: List[PaymentOption],
    amount_safe_today: Decimal,
    earliest_full_date: Optional[date],
    salary_updates: Optional[Dict[str, Decimal]] = None,
    spending_variants: Optional[List[dict]] = None,
) -> List[CandidatePlan]:
    """
    Generate all candidate plans and return them sorted by the ranking rules.
    
    Ranking rules (in order):
    1. Completes by desired_completion_date
    2. No spending changes required
    3. Minimize total amount paid
    4. Start payment earlier
    5. Fewer payments
    6. Lowest payment_option_id as final tie-breaker
    """
    candidates = []
    uid = request.user_id
    rid = request.request_id
    req_date = request.request_date
    req_amount = request.requested_amount
    deadline = request.desired_completion_date
    user_methods = set(profile.payment_methods_user_will_consider)
    
    # --- Candidate A: Full payment now ---
    if FULL_PAYMENT in user_methods:
        _add_full_payment_candidates(
            candidates, request, profile, events, patterns,
            payment_options, amount_safe_today, salary_updates
        )
    
    # --- Candidate B: Partial payment ---
    if request.allows_partial_payment and PARTIAL_PAYMENT in user_methods:
        _add_partial_payment_candidates(
            candidates, request, profile, events, patterns,
            amount_safe_today, earliest_full_date, salary_updates
        )
    
    # --- Candidate C: Installments ---
    if INSTALLMENTS in user_methods:
        _add_installment_candidates(
            candidates, request, profile, events, patterns,
            payment_options, salary_updates
        )
    
    # --- Candidate D: Wait ---
    if FULL_PAYMENT in user_methods and earliest_full_date is not None:
        _add_wait_candidate(
            candidates, request, profile, events, patterns,
            earliest_full_date, salary_updates
        )
    
    # --- Spending change variants ---
    if spending_variants:
        for variant in spending_variants:
            _add_spending_variant_candidates(
                candidates, request, profile, events, patterns,
                payment_options, variant, salary_updates
            )
    
    # --- Fallback: not_recommended ---
    if not candidates or all(c.safety_status == "unsafe" for c in candidates):
        candidates.append(CandidatePlan(
            candidate_id=f"{rid}_not_recommended",
            payment_method=NOT_RECOMMENDED,
            payment_option_id=None,
            payment_schedule=[],
            total_amount_paid=ZERO,
            completion_date=None,
            spending_changes=[],
            minimum_forecast_balance=_get_baseline_min_balance(profile, events, patterns, req_date, salary_updates),
            deadline_met=False,
            user_preference_allowed=True,
            safety_status="safe",
            reason_codes=["no_safe_plan_available"],
            requires_spending_changes=False,
            num_payments=0,
            starts_on_request_date=False,
        ))
    
    # Filter to only safe candidates (unless all are unsafe, then keep not_recommended)
    safe_candidates = [c for c in candidates if c.safety_status == "safe"]
    if not safe_candidates:
        safe_candidates = [c for c in candidates if c.payment_method == NOT_RECOMMENDED]
    
    # Sort per ranking rules
    safe_candidates.sort(key=_ranking_key)
    
    return safe_candidates


def _ranking_key(c: CandidatePlan):
    """Return sorting key for candidate plans (lower = better)."""
    # 1. Completes by deadline (True = good = 0)
    not_by_deadline = 0 if c.deadline_met else 1
    # 2. No spending changes (False = no changes = 0)
    has_changes = 1 if c.requires_spending_changes else 0
    # 3. Minimize total amount paid
    total = c.total_amount_paid or ZERO
    # 4. Start payment earlier (earlier = lower date number)
    if c.payment_schedule:
        first_date = c.payment_schedule[0][0]
    else:
        first_date = date(9999, 1, 1)
    # 5. Fewer payments
    num = c.num_payments
    # 6. payment_option_id (lower = better)
    opt_id = c.payment_option_id or "zzz"
    
    return (not_by_deadline, has_changes, total, first_date, num, opt_id)


def _get_baseline_min_balance(
    profile: FinancialProfile,
    events: List[FinancialEvent],
    patterns: List[dict],
    request_date: date,
    salary_updates: Optional[Dict[str, Decimal]] = None,
) -> Decimal:
    """Get minimum balance without any candidate payments."""
    days = simulate_cashflow(profile, events, patterns, request_date,
                             salary_updates=salary_updates)
    return get_minimum_balance_in_period(days)


def _add_full_payment_candidates(
    candidates: List[CandidatePlan],
    request: Request,
    profile: FinancialProfile,
    events: List[FinancialEvent],
    patterns: List[dict],
    payment_options: List[PaymentOption],
    amount_safe_today: Decimal,
    salary_updates: Optional[Dict[str, Decimal]] = None,
):
    """Add full_payment candidate(s)."""
    req_amount = request.requested_amount
    
    # Try each full_payment option
    full_opts = [o for o in payment_options if o.payment_method == FULL_PAYMENT]
    
    if not full_opts:
        # No explicit full payment option; try paying full amount on request_date
        if amount_safe_today >= req_amount:
            days = simulate_cashflow(
                profile, events, patterns, request.request_date,
                extra_debits=[(request.request_date, req_amount)],
                salary_updates=salary_updates,
            )
            min_bal = get_minimum_balance_in_period(days)
            is_safe = min_bal >= profile.minimum_balance_to_keep
            deadline_met = request.request_date <= request.desired_completion_date
            
            candidates.append(CandidatePlan(
                candidate_id=f"{request.request_id}_full",
                payment_method=FULL_PAYMENT,
                payment_option_id=None,
                payment_schedule=[(request.request_date, req_amount)],
                total_amount_paid=req_amount,
                completion_date=request.request_date,
                spending_changes=[],
                minimum_forecast_balance=min_bal,
                deadline_met=deadline_met,
                user_preference_allowed=True,
                safety_status="safe" if is_safe else "unsafe",
                reason_codes=[] if is_safe else ["would_violate_minimum_balance"],
                requires_spending_changes=False,
                num_payments=1,
                starts_on_request_date=True,
            ))
        return
    
    for opt in full_opts:
        pay_date = opt.first_payment_date or request.request_date
        
        # Check if paying this option is safe
        days = simulate_cashflow(
            profile, events, patterns, request.request_date,
            extra_debits=[(pay_date, opt.payment_amount)],
            salary_updates=salary_updates,
        )
        min_bal = get_minimum_balance_in_period(days)
        is_safe = min_bal >= profile.minimum_balance_to_keep
        deadline_met = pay_date <= request.desired_completion_date
        
        candidates.append(CandidatePlan(
            candidate_id=f"{request.request_id}_full_{opt.payment_option_id}",
            payment_method=FULL_PAYMENT,
            payment_option_id=opt.payment_option_id,
            payment_schedule=[(pay_date, opt.payment_amount)],
            total_amount_paid=opt.total_payable_amount,
            completion_date=pay_date,
            spending_changes=[],
            minimum_forecast_balance=min_bal,
            deadline_met=deadline_met,
            user_preference_allowed=True,
            safety_status="safe" if is_safe else "unsafe",
            reason_codes=[] if is_safe else ["would_violate_minimum_balance"],
            requires_spending_changes=False,
            num_payments=1,
            starts_on_request_date=(pay_date == request.request_date),
        ))


def _add_partial_payment_candidates(
    candidates: List[CandidatePlan],
    request: Request,
    profile: FinancialProfile,
    events: List[FinancialEvent],
    patterns: List[dict],
    amount_safe_today: Decimal,
    earliest_full_date: Optional[date],
    salary_updates: Optional[Dict[str, Decimal]] = None,
):
    """Add partial_payment candidate."""
    req_amount = request.requested_amount
    
    if amount_safe_today <= ZERO:
        return
    if amount_safe_today >= req_amount:
        return  # Full payment is possible, no partial needed
    if earliest_full_date is None:
        return
    if earliest_full_date > request.desired_completion_date:
        return  # Can't complete remaining by deadline
    
    # Partial payment: amount_safe_today now, remainder on earliest_full_date
    remainder = req_amount - amount_safe_today
    
    # Verify the plan is actually safe
    days = simulate_cashflow(
        profile, events, patterns, request.request_date,
        extra_debits=[
            (request.request_date, amount_safe_today),
            (earliest_full_date, remainder),
        ],
        salary_updates=salary_updates,
    )
    min_bal = get_minimum_balance_in_period(days)
    is_safe = min_bal >= profile.minimum_balance_to_keep
    deadline_met = earliest_full_date <= request.desired_completion_date
    
    if is_safe:
        candidates.append(CandidatePlan(
            candidate_id=f"{request.request_id}_partial",
            payment_method=PARTIAL_PAYMENT,
            payment_option_id=None,
            payment_schedule=[
                (request.request_date, amount_safe_today),
                (earliest_full_date, remainder),
            ],
            total_amount_paid=req_amount,
            completion_date=earliest_full_date,
            spending_changes=[],
            minimum_forecast_balance=min_bal,
            deadline_met=deadline_met,
            user_preference_allowed=True,
            safety_status="safe",
            reason_codes=[],
            requires_spending_changes=False,
            num_payments=2,
            starts_on_request_date=True,
        ))


def _add_installment_candidates(
    candidates: List[CandidatePlan],
    request: Request,
    profile: FinancialProfile,
    events: List[FinancialEvent],
    patterns: List[dict],
    payment_options: List[PaymentOption],
    salary_updates: Optional[Dict[str, Decimal]] = None,
):
    """Add installment candidates from payment options."""
    installment_opts = [o for o in payment_options if o.payment_method == INSTALLMENTS]
    max_months = profile.max_installment_months
    
    for opt in installment_opts:
        # Check max installment months constraint
        if max_months is not None:
            # Approximate months = number_of_payments * frequency_days / 30
            approx_months = (opt.number_of_payments * (opt.payment_frequency_days or 30)) / 30
            if approx_months > max_months:
                continue
        
        # Build payment schedule
        schedule = _build_payment_schedule(opt)
        
        # Check if all payments fall within reasonable bounds
        if not schedule:
            continue
        
        last_payment_date = schedule[-1][0]
        if last_payment_date > request.desired_completion_date + timedelta(days=7):
            # Allow a small buffer of 7 days
            pass  # Don't skip, just mark as not meeting deadline
        
        # Check financial safety
        extra_debits = [(pay_date, amount) for pay_date, amount in schedule]
        
        days = simulate_cashflow(
            profile, events, patterns, request.request_date,
            extra_debits=extra_debits,
            salary_updates=salary_updates,
        )
        min_bal = get_minimum_balance_in_period(days)
        is_safe = min_bal >= profile.minimum_balance_to_keep
        deadline_met = last_payment_date <= request.desired_completion_date
        
        candidates.append(CandidatePlan(
            candidate_id=f"{request.request_id}_inst_{opt.payment_option_id}",
            payment_method=INSTALLMENTS,
            payment_option_id=opt.payment_option_id,
            payment_schedule=schedule,
            total_amount_paid=opt.total_payable_amount,
            completion_date=last_payment_date,
            spending_changes=[],
            minimum_forecast_balance=min_bal,
            deadline_met=deadline_met,
            user_preference_allowed=True,
            safety_status="safe" if is_safe else "unsafe",
            reason_codes=[] if is_safe else ["would_violate_minimum_balance"],
            requires_spending_changes=False,
            num_payments=opt.number_of_payments,
            starts_on_request_date=(schedule[0][0] == request.request_date),
        ))


def _add_wait_candidate(
    candidates: List[CandidatePlan],
    request: Request,
    profile: FinancialProfile,
    events: List[FinancialEvent],
    patterns: List[dict],
    earliest_full_date: date,
    salary_updates: Optional[Dict[str, Decimal]] = None,
):
    """Add wait candidate."""
    req_amount = request.requested_amount
    
    # Simulate paying the full amount on earliest_full_date
    days = simulate_cashflow(
        profile, events, patterns, request.request_date,
        extra_debits=[(earliest_full_date, req_amount)],
        salary_updates=salary_updates,
    )
    min_bal = get_minimum_balance_in_period(days)
    is_safe = min_bal >= profile.minimum_balance_to_keep
    deadline_met = earliest_full_date <= request.desired_completion_date
    
    if is_safe:
        candidates.append(CandidatePlan(
            candidate_id=f"{request.request_id}_wait",
            payment_method=WAIT,
            payment_option_id=None,
            payment_schedule=[(earliest_full_date, req_amount)],
            total_amount_paid=req_amount,
            completion_date=earliest_full_date,
            spending_changes=[],
            minimum_forecast_balance=min_bal,
            deadline_met=deadline_met,
            user_preference_allowed=True,
            safety_status="safe",
            reason_codes=[],
            requires_spending_changes=False,
            num_payments=1,
            starts_on_request_date=(earliest_full_date == request.request_date),
        ))


def _add_spending_variant_candidates(
    candidates: List[CandidatePlan],
    request: Request,
    profile: FinancialProfile,
    events: List[FinancialEvent],
    patterns: List[dict],
    payment_options: List[PaymentOption],
    variant: dict,
    salary_updates: Optional[Dict[str, Decimal]] = None,
):
    """Add candidates that require spending changes."""
    spending_overrides = variant.get("overrides", {})
    change_strings = variant.get("changes", [])
    
    if not spending_overrides:
        return
    
    # Recalculate what's safe with these spending changes
    full_opts = [o for o in payment_options if o.payment_method == FULL_PAYMENT]
    
    # Try full payment first
    req_amount = request.requested_amount
    
    # Try paying full amount now with spending changes
    days = simulate_cashflow(
        profile, events, patterns, request.request_date,
        extra_debits=[(request.request_date, req_amount)],
        spending_overrides=spending_overrides,
        salary_updates=salary_updates,
    )
    min_bal = get_minimum_balance_in_period(days)
    is_safe = min_bal >= profile.minimum_balance_to_keep
    
    if is_safe and FULL_PAYMENT in profile.payment_methods_user_will_consider:
        deadline_met = request.request_date <= request.desired_completion_date
        candidates.append(CandidatePlan(
            candidate_id=f"{request.request_id}_spend_full_{len(candidates)}",
            payment_method=FULL_PAYMENT,
            payment_option_id=full_opts[0].payment_option_id if full_opts else None,
            payment_schedule=[(request.request_date, req_amount)],
            total_amount_paid=req_amount,
            completion_date=request.request_date,
            spending_changes=change_strings,
            minimum_forecast_balance=min_bal,
            deadline_met=deadline_met,
            user_preference_allowed=True,
            safety_status="safe",
            reason_codes=[],
            requires_spending_changes=True,
            num_payments=1,
            starts_on_request_date=True,
        ))
        return
    
    # Try installments with spending changes
    if INSTALLMENTS in profile.payment_methods_user_will_consider:
        inst_opts = [o for o in payment_options if o.payment_method == INSTALLMENTS]
        for opt in inst_opts:
            schedule = _build_payment_schedule(opt)
            extra_debits = [(d, a) for d, a in schedule]
            
            days = simulate_cashflow(
                profile, events, patterns, request.request_date,
                extra_debits=extra_debits,
                spending_overrides=spending_overrides,
                salary_updates=salary_updates,
            )
            min_bal = get_minimum_balance_in_period(days)
            is_safe = min_bal >= profile.minimum_balance_to_keep
            
            if is_safe:
                last_date = schedule[-1][0] if schedule else request.request_date
                deadline_met = last_date <= request.desired_completion_date
                candidates.append(CandidatePlan(
                    candidate_id=f"{request.request_id}_spend_inst_{opt.payment_option_id}",
                    payment_method=INSTALLMENTS,
                    payment_option_id=opt.payment_option_id,
                    payment_schedule=schedule,
                    total_amount_paid=opt.total_payable_amount,
                    completion_date=last_date,
                    spending_changes=change_strings,
                    minimum_forecast_balance=min_bal,
                    deadline_met=deadline_met,
                    user_preference_allowed=True,
                    safety_status="safe",
                    reason_codes=[],
                    requires_spending_changes=True,
                    num_payments=opt.number_of_payments,
                    starts_on_request_date=(schedule[0][0] == request.request_date if schedule else False),
                ))
                break  # Take first safe installment option


def determine_affordability_status(
    best_candidate: CandidatePlan,
    amount_safe_today: Decimal,
    requested_amount: Decimal,
    earliest_full_date: Optional[date],
    request_date: date,
    profile: FinancialProfile,
) -> str:
    """Determine the affordability_status enum value."""
    method = best_candidate.payment_method
    
    if method == NOT_RECOMMENDED:
        return NOT_AFFORDABLE
    
    if method == FULL_PAYMENT and not best_candidate.requires_spending_changes:
        if best_candidate.payment_schedule and best_candidate.payment_schedule[0][0] == request_date:
            return AFFORDABLE_NOW
        elif earliest_full_date and earliest_full_date > request_date:
            return AFFORDABLE_LATER
    
    if method == WAIT:
        return AFFORDABLE_LATER
    
    if method in (PARTIAL_PAYMENT, INSTALLMENTS) or best_candidate.requires_spending_changes:
        return AFFORDABLE_WITH_PLAN
    
    if method == FULL_PAYMENT and best_candidate.payment_schedule:
        first_date = best_candidate.payment_schedule[0][0]
        if first_date == request_date:
            return AFFORDABLE_NOW
        else:
            return AFFORDABLE_LATER
    
    return NOT_AFFORDABLE


def format_payment_plan(candidate: CandidatePlan) -> str:
    """Format the payment plan as the required string."""
    if candidate.payment_method == NOT_RECOMMENDED or not candidate.payment_schedule:
        return "none"
    
    parts = []
    for pay_date, amount in candidate.payment_schedule:
        # Always round to 2 decimal places to avoid Decimal precision artifacts
        rounded = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if rounded == rounded.to_integral_value():
            amount_str = str(int(rounded))
        else:
            amount_str = str(rounded)
        parts.append(f"{pay_date.strftime('%Y-%m-%d')}:{amount_str}")
    
    return "|".join(parts)


def format_spending_changes(candidate: CandidatePlan) -> str:
    """Format spending changes as the required string."""
    if not candidate.spending_changes:
        return "none"
    return "|".join(candidate.spending_changes)
