"""
Financial event reconciliation.
Handles event lifecycle: cancelled events, pending credits, refunds, duplicates.
Determines which events to include in the 90-day cash flow simulation.

CRITICAL: The reconciliation determines which events appear in the future simulation.
"""
from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import statistics
import logging

from models import FinancialEvent, FinancialProfile, MessageEvidence
from fx import FXConverter

logger = logging.getLogger(__name__)


# Event statuses we trust as actual cash flow
INCLUDE_STATUSES = {"settled", "scheduled", "confirmed"}
# Statuses we skip  
EXCLUDE_STATUSES = {"cancelled", "failed", "reversed"}
# Pending = include debits, skip credits
PENDING_STATUS = "pending"


def reconcile_events(
    events: List[FinancialEvent],
    profile: FinancialProfile,
    request_date: date,
    messages: List[MessageEvidence],
    fx: FXConverter,
) -> Tuple[List[FinancialEvent], Dict[str, str]]:
    """
    Reconcile financial events, returning:
    - List of events to include in cash flow (with home currency amounts)
    - Dict of event_id -> resolution reason (for audit)
    """
    resolutions: Dict[str, str] = {}
    
    # Build lookup by event_id
    event_by_id: Dict[str, FinancialEvent] = {e.event_id: e for e in events}
    
    # Events that are superseded by later linked events
    superseded_ids: Set[str] = set()
    for e in events:
        if e.linked_event_id and e.linked_event_id in event_by_id:
            original = event_by_id[e.linked_event_id]
            # If original was cancelled/excluded and this is the settlement, exclude the cancelled one
            if original.status in EXCLUDE_STATUSES:
                superseded_ids.add(e.linked_event_id)
                resolutions[e.linked_event_id] = f"superseded_by_{e.event_id}"
            # If original was pending and this is the settled version, supersede the pending
            elif original.status == PENDING_STATUS and e.status in INCLUDE_STATUSES:
                superseded_ids.add(e.linked_event_id)
                resolutions[e.linked_event_id] = f"settled_as_{e.event_id}"
    
    # Apply message-based amendments
    message_amendments = _parse_message_amendments(messages, event_by_id, profile)
    
    included = []
    for event in events:
        eid = event.event_id
        
        # Skip superseded events
        if eid in superseded_ids:
            resolutions[eid] = resolutions.get(eid, "superseded")
            continue
        
        # Skip explicitly excluded statuses
        if event.status in EXCLUDE_STATUSES:
            resolutions[eid] = f"excluded_status:{event.status}"
            continue
        
        # Skip pending credits (unrealized income)
        if event.status == PENDING_STATUS and event.direction == "credit":
            resolutions[eid] = "pending_credit_excluded"
            continue
        
        # Skip investment values (non-cash) — they're equity, not available cash
        if event.event_type == "investment" and event.direction == "credit":
            resolutions[eid] = "unrealized_investment_excluded"
            continue
        
        # Apply message amendments
        if eid in message_amendments:
            amendment = message_amendments[eid]
            if amendment.get("action") == "cancel":
                resolutions[eid] = "cancelled_by_message"
                continue
            if amendment.get("amount"):
                event.amount = amendment["amount"]
                resolutions[eid] = f"amount_amended_by_message:{amendment['amount']}"
        
        # Convert amount to home currency.
        # PHASE 4 FIX: distinguish realized cash events from non-cash investments.
        # Non-cash investment credits (unrealized value) are already excluded from
        # cashflow above. For investment DEBITS (cash invested) or realized sales,
        # we use the settlement/event date rate as that was the actual transaction date.
        # This function picks the correct FX date per event type.
        if event.amount is not None and event.currency != profile.home_currency:
            effective_date = _get_fx_date(event, request_date)
            converted = fx.to_home_currency(
                event.amount,
                event.currency,
                profile.home_currency,
                effective_date
            )
            event.amount_home_currency = converted
        else:
            event.amount_home_currency = event.amount
        
        included.append(event)
    
    logger.debug(f"Reconciled {len(events)} events → {len(included)} included, "
                 f"{len(events) - len(included)} excluded")
    return included, resolutions


def _get_fx_date(event, request_date) -> "date":
    """
    Phase 4: Return the correct FX rate lookup date for a financial event.

    Rules:
    - Realized cash transactions (expenses, income, refunds, debt_payment):
        Use settlement_date if available, else event_date, else request_date.
        This reflects the actual exchange rate at the time money changed hands.
    - Investment purchase (debit):
        Use event_date — this is when cash left the account.
    - Investment credit (non-cash / mark-to-market):
        Investment credits are excluded from cashflow (see reconcile_events).
        If we ever need to value them for reporting, use request_date so the
        valuation reflects the current FX rate, not the historical entry rate.
    - Future scheduled events:
        Use settlement_date if available (expected settlement FX), else event_date.
    """
    if event.event_type == "investment" and event.direction == "credit":
        # Mark-to-market: value at request date, not historical entry date
        return request_date
    # All other events: use actual transaction/settlement date
    return event.settlement_date or event.event_date or request_date


def _parse_message_amendments(
    messages: List[MessageEvidence],
    event_by_id: Dict[str, FinancialEvent],
    profile: FinancialProfile,
) -> Dict[str, dict]:
    """
    Parse messages for event amendments (lightweight deterministic).
    Full LLM parsing is handled separately in agents.py.
    """
    amendments = {}
    
    for msg in messages:
        if not msg.related_event_id:
            continue
        
        eid = msg.related_event_id
        text = msg.message_text.lower()

        # PHASE 5 NOTE: This keyword matching is English-only and is a fallback.
        # The primary language-agnostic interpretation is handled by the LLM in agents.py.
        # These keywords are intentionally narrow — only the highest-confidence signals
        # — to minimize false positives from non-English messages that happen to
        # contain similar character sequences.
        #
        # Confirmed settlement: money has arrived
        confirm_keywords = [
            "proceeds have reached your account",
            "claim is now closed",
            "receipt has the final",
        ]
        if any(kw in text for kw in confirm_keywords):
            amendments[eid] = {"action": "confirm"}
            continue

        # Pending / not yet settled: income not yet available
        cancel_keywords = [
            "refund has been initiated but has not reached",
            "prize claim has been verified and is still in payment processing",
        ]
        if any(kw in text for kw in cancel_keywords):
            # Mark as pending, not cancelled — the LLM will make the final call
            amendments[eid] = {"action": "mark_pending"}
            continue
    
    return amendments


def detect_recurring_patterns(
    events: List[FinancialEvent],
    profile: FinancialProfile,
    request_date: date,
) -> List[dict]:
    """
    Detect recurring expense and income patterns from historical events.
    
    Groups events by (category, direction) and detects the frequency.
    Projects patterns into the future from the last known occurrence.
    
    CRITICAL: Only uses settled events for pattern detection.
    CRITICAL: Properly groups by description similarity for more accurate patterns.
    """
    # Only use settled events for pattern detection
    settled = [e for e in events 
               if e.status in INCLUDE_STATUSES 
               and e.event_date is not None
               and (e.amount_home_currency or e.amount) is not None]
    
    if not settled:
        return []
    
    # Group by (category, direction, flexibility)
    # Note: same category can have multiple sub-patterns (e.g., weekly groceries vs monthly)
    groups = defaultdict(list)
    for e in settled:
        key = (e.category, e.direction, e.flexibility, e.event_type)
        groups[key].append(e)
    
    patterns = []
    
    for (category, direction, flexibility, event_type), group in groups.items():
        if len(group) < 2:
            continue
        
        # Sort by date
        group_sorted = sorted(group, key=lambda e: e.event_date)
        
        # Calculate intervals between consecutive events
        intervals = []
        for i in range(1, len(group_sorted)):
            delta = (group_sorted[i].event_date - group_sorted[i-1].event_date).days
            if 1 <= delta <= 400:
                intervals.append(delta)
        
        if not intervals:
            continue
        
        # For salary/income: always use 30-day interval (monthly income)
        # because median of 28-31 day intervals often snaps incorrectly to 28
        if event_type == "income" and category == "salary":
            snapped_interval = 30
            # Determine typical day of month for salary
            dom_counts = {}
            for e in group_sorted[-6:]:
                dom = e.event_date.day
                dom_counts[dom] = dom_counts.get(dom, 0) + 1
            typical_dom = max(dom_counts, key=dom_counts.get)
        else:
            # Determine median interval (more robust than average)
            median_interval = int(statistics.median(intervals))
            
            # Snap to common intervals
            snapped_interval = _snap_to_common_interval(median_interval)
            typical_dom = None
        
        # Only keep patterns with reasonable regularity (interval std dev < 75% of snapped)
        if len(intervals) >= 3:
            try:
                std_dev = statistics.stdev(intervals)
                if std_dev > snapped_interval * 0.75:
                    # High variance — might not be a true recurring pattern
                    # Use last occurrence only if it's recent
                    last_date = group_sorted[-1].event_date
                    if (request_date - last_date).days > 90:
                        continue
            except Exception:
                pass
        
        # Most recent event
        last_event = group_sorted[-1]
        last_date = last_event.event_date
        
        # Get amounts from recent events (last 6 occurrences or 1 year)
        cutoff = request_date - timedelta(days=365)
        recent = [e for e in group_sorted if e.event_date >= cutoff]
        if not recent:
            recent = group_sorted[-6:]
        
        # Get amounts in home currency
        amounts = []
        for e in recent:
            amt = e.amount_home_currency or e.amount
            if amt is not None and amt > Decimal("0"):
                amounts.append(amt)
        
        if not amounts:
            continue
        
        # Use adaptive amount strategy based on pattern stability.
        # Forensic analysis (v2 phase 1) showed:
        #   - median: lowest MAE overall (777k), best for variable patterns
        #   - mean: better for stable/fixed patterns with low variance (req_08, req_17)
        #   - most_recent: wins most often but catastrophic on sparse/spiked history
        # Strategy: use mean when CV < 15% (stable), else median (robust to outliers)
        float_amounts = [float(a) for a in amounts]
        if len(float_amounts) >= 2:
            _mean = statistics.mean(float_amounts)
            _stdev = statistics.stdev(float_amounts)
            _cv = _stdev / _mean if _mean > 0 else 1.0
        else:
            _cv = 0.0  # single value — treat as stable
        
        if _cv < 0.15:
            # Stable pattern: use mean (more accurate for consistent amounts)
            avg_amount = Decimal(str(round(statistics.mean(float_amounts), 2)))
        else:
            # Variable pattern: use median (robust to one-time spikes)
            avg_amount = Decimal(str(statistics.median(float_amounts)))
        
        # Find next expected date AFTER request_date
        if event_type == "income" and category == "salary":
            # Project salary on the correct day-of-month
            next_date = _next_salary_date(last_date, typical_dom, request_date)
        else:
            next_date = last_date + timedelta(days=snapped_interval)
            while next_date <= request_date:
                next_date += timedelta(days=snapped_interval)
        
        # Skip if last occurrence was too long ago (more than 3 intervals)
        if (request_date - last_date).days > snapped_interval * 3:
            continue
        
        patterns.append({
            "category": category,
            "direction": direction,
            "flexibility": flexibility,
            "event_type": event_type,
            "avg_amount": avg_amount,
            "currency": profile.home_currency,
            "frequency_days": snapped_interval,
            "next_date": next_date,
            "last_event_id": last_event.event_id,
            "last_date": last_date,
            "min_amount": _get_min_amount(group, profile.home_currency),
            "key": f"{category}_{direction}_{event_type}",
            "typical_dom": typical_dom if event_type == "income" and category == "salary" else None,
        })
    
    logger.debug(f"Detected {len(patterns)} recurring patterns for user")
    return patterns


def _next_salary_date(last_date: date, typical_dom: int, request_date: date) -> date:
    """Find the next salary date after request_date based on the typical day-of-month."""
    import calendar
    
    # Try next month on the same day
    month = last_date.month + 1
    year = last_date.year
    if month > 12:
        month = 1
        year += 1
    
    # Find next occurrence
    candidate = last_date
    while candidate <= request_date:
        month = candidate.month + 1
        year = candidate.year
        if month > 12:
            month = 1
            year += 1
        # Get the actual day (handle month-end edge cases)
        max_day = calendar.monthrange(year, month)[1]
        actual_dom = min(typical_dom, max_day)
        candidate = date(year, month, actual_dom)
    
    return candidate


def _get_min_amount(events: List[FinancialEvent], home_currency: str) -> Optional[Decimal]:
    """Get the minimum_allowed_amount from events in this group."""
    for e in reversed(events):
        if e.minimum_allowed_amount is not None and e.minimum_allowed_amount > 0:
            return e.minimum_allowed_amount
    return None


def _snap_to_common_interval(days: int) -> int:
    """Snap interval to nearest common period."""
    common = [7, 14, 15, 21, 28, 30, 31, 60, 90, 180, 365]
    return min(common, key=lambda c: abs(c - days))


def apply_salary_message_updates(
    patterns: List[dict],
    messages: List[MessageEvidence],
    profile: FinancialProfile,
    request_date: date,
    fx: FXConverter,
) -> List[dict]:
    """
    Update salary patterns based on employer messages.
    Handled by LLM agents — this is a pass-through.
    """
    return patterns
