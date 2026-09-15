"""
Spending change optimizer.
Searches for flexible expense modifications that make a plan feasible.
Only modifies expenses explicitly marked as flexible (stoppable/reducible).
Maximum 3 changes. Cannot stop AND reduce the same event.
Prefers minimum intervention needed.
"""
from decimal import Decimal
from datetime import date
from typing import List, Optional, Dict, Tuple
import logging
from itertools import combinations

from models import FinancialEvent, FinancialProfile
from cashflow import (
    simulate_cashflow, is_plan_safe, get_minimum_balance_in_period,
    find_amount_safe_to_pay
)
from config import FLEXIBILITY_STOPPABLE, FLEXIBILITY_REDUCIBLE, FLEXIBILITY_REDUCIBLE_OR_STOPPABLE

logger = logging.getLogger(__name__)
ZERO = Decimal("0")


def find_spending_changes(
    profile: FinancialProfile,
    events: List[FinancialEvent],
    patterns: List[dict],
    request_date: date,
    requested_amount: Decimal,
    salary_updates: Optional[Dict[str, Decimal]] = None,
    max_changes: int = 3,
) -> List[dict]:
    """
    Find spending changes that would make a plan feasible.
    
    Returns a list of variant dicts, each with:
    - overrides: dict of event_id -> {action: stop/reduce_to, new_amount}
    - changes: list of formatted change strings
    - description: human-readable description
    
    Strategy:
    1. Try stopping/reducing one flexible expense at a time (min intervention)
    2. Try combinations of 2, then 3 changes
    3. For reducible expenses, try reducing to minimum_allowed_amount
    4. Prefer stopping over reducing (simpler)
    5. Respect user's willingness to stop/reduce by category
    """
    variants = []
    
    # Get flexible expenses from patterns (recurring)
    flexible_patterns = [
        p for p in patterns
        if p["direction"] == "debit" and p["flexibility"] in 
           (FLEXIBILITY_STOPPABLE, FLEXIBILITY_REDUCIBLE, FLEXIBILITY_REDUCIBLE_OR_STOPPABLE)
    ]
    
    if not flexible_patterns:
        return []
    
    # Filter by user's willingness
    user_can_stop_cats = set(profile.expense_categories_willing_to_stop)
    user_can_reduce_cats = set(profile.expense_categories_willing_to_reduce)
    
    # Build list of possible single changes
    possible_stops = []
    possible_reduces = []
    
    for p in flexible_patterns:
        cat = p["category"]
        flex = p["flexibility"]
        eid = p["last_event_id"]
        
        can_stop = (
            flex in (FLEXIBILITY_STOPPABLE, FLEXIBILITY_REDUCIBLE_OR_STOPPABLE) and
            cat in user_can_stop_cats
        )
        can_reduce = (
            flex in (FLEXIBILITY_REDUCIBLE, FLEXIBILITY_REDUCIBLE_OR_STOPPABLE) and
            cat in user_can_reduce_cats and
            p.get("min_amount") is not None
        )
        
        if can_stop:
            possible_stops.append({
                "event_id": eid,
                "category": cat,
                "pattern": p,
                "action": "stop",
                "savings_per_period": p["avg_amount"],
            })
        
        if can_reduce and p.get("min_amount") is not None:
            savings = p["avg_amount"] - p["min_amount"]
            if savings > ZERO:
                possible_reduces.append({
                    "event_id": eid,
                    "category": cat,
                    "pattern": p,
                    "action": "reduce_to",
                    "new_amount": p["min_amount"],
                    "savings_per_period": savings,
                })
    
    all_possible = possible_stops + possible_reduces
    
    # Sort by savings (highest first for efficiency)
    all_possible.sort(key=lambda x: x["savings_per_period"], reverse=True)
    
    # Try single changes first
    for change in all_possible:
        variant = _make_variant([change])
        if _variant_makes_payment_feasible(
            profile, events, patterns, request_date, requested_amount,
            variant, salary_updates
        ):
            variants.append(variant)
    
    # Try pairs
    if not variants and max_changes >= 2:
        for c1, c2 in combinations(all_possible[:10], 2):
            # Cannot stop AND reduce same event
            if c1["event_id"] == c2["event_id"]:
                continue
            variant = _make_variant([c1, c2])
            if _variant_makes_payment_feasible(
                profile, events, patterns, request_date, requested_amount,
                variant, salary_updates
            ):
                variants.append(variant)
    
    # Try triples
    if not variants and max_changes >= 3:
        for c1, c2, c3 in combinations(all_possible[:8], 3):
            # Cannot stop AND reduce same event
            eids = [c1["event_id"], c2["event_id"], c3["event_id"]]
            if len(set(eids)) != len(eids):
                continue
            variant = _make_variant([c1, c2, c3])
            if _variant_makes_payment_feasible(
                profile, events, patterns, request_date, requested_amount,
                variant, salary_updates
            ):
                variants.append(variant)
    
    return variants[:5]  # Return up to 5 viable variants


def _make_variant(changes: List[dict]) -> dict:
    """Create a variant dict from a list of individual changes."""
    overrides = {}
    change_strings = []
    
    for change in changes:
        eid = change["event_id"]
        action = change["action"]
        
        if action == "stop":
            overrides[eid] = {"action": "stop"}
            change_strings.append(f"stop:{eid}")
        elif action == "reduce_to":
            new_amount = change["new_amount"]
            overrides[eid] = {"action": "reduce_to", "new_amount": new_amount}
            change_strings.append(f"reduce_to:{eid}:{new_amount.quantize(Decimal('0.01'))}")
    
    return {
        "overrides": overrides,
        "changes": change_strings,
        "description": f"Spending changes: {', '.join(change_strings)}",
    }


def _variant_makes_payment_feasible(
    profile: FinancialProfile,
    events: List[FinancialEvent],
    patterns: List[dict],
    request_date: date,
    requested_amount: Decimal,
    variant: dict,
    salary_updates: Optional[Dict[str, Decimal]] = None,
) -> bool:
    """Check if applying a spending variant makes full payment feasible."""
    overrides = variant.get("overrides", {})
    
    # Try paying the full amount now with spending changes
    from cashflow import simulate_cashflow, is_plan_safe, get_minimum_balance_in_period
    
    days = simulate_cashflow(
        profile, events, patterns, request_date,
        extra_debits=[(request_date, requested_amount)],
        spending_overrides=overrides,
        salary_updates=salary_updates,
    )
    
    return is_plan_safe(days, profile.minimum_balance_to_keep)
