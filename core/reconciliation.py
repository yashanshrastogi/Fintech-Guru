from enum import Enum
from typing import List, Dict, Set, Tuple
from decimal import Decimal
import logging

from core.models import FinancialEvent, FinancialProfile, MessageEvidence
from core.fx import FXConverter

logger = logging.getLogger(__name__)

class EventStatus(str, Enum):
    INITIATED = "initiated"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SETTLED = "settled"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REVERSED = "reversed"
    AMENDED = "amended"
    DUPLICATE = "duplicate"

class EventLifecycle:
    """
    Formal state machine and precedence rules for transaction lifecycles.
    """
    
    # Statuses that explicitly do not affect available cash
    NON_CASH_STATUSES = {
        EventStatus.CANCELLED,
        EventStatus.FAILED,
        EventStatus.REVERSED,
        EventStatus.DUPLICATE
    }
    
    # Statuses that are fully trusted as realized or guaranteed cashflow
    REALIZED_STATUSES = {
        EventStatus.SETTLED,
        EventStatus.CONFIRMED,
        EventStatus.SCHEDULED
    }

    @staticmethod
    def should_include(event: FinancialEvent, is_amended: bool = False) -> bool:
        """Determines if an event should be included in cashflow forecasting."""
        if is_amended or event.status in EventLifecycle.NON_CASH_STATUSES:
            return False
            
        # Unrealized investment credits are not liquid cash
        if event.event_type == "investment" and event.direction == "credit":
            return False
            
        # Pending credits (income) are not trusted until settled/confirmed
        if event.status == EventStatus.PENDING and event.direction == "credit":
            return False
            
        # Pending debits (expenses) ARE included to be conservative with cash
        if event.status == EventStatus.PENDING and event.direction == "debit":
            return True
            
        if event.status in EventLifecycle.REALIZED_STATUSES:
            return True
            
        # Initiated behaves like pending
        if event.status == EventStatus.INITIATED and event.direction == "debit":
            return True
            
        return False

def reconcile_events(
    events: List[FinancialEvent],
    profile: FinancialProfile,
    request_date: str,
    messages: List[MessageEvidence],
    fx: FXConverter,
) -> Tuple[List[FinancialEvent], Dict[str, str]]:
    """
    Reconcile financial events using deterministic precedence rules.
    Returns:
    - List of events to include in cash flow (amounts converted to home currency)
    - Dict of event_id -> resolution reason (for audit)
    """
    resolutions: Dict[str, str] = {}
    event_by_id: Dict[str, FinancialEvent] = {e.event_id: e for e in events}
    
    # 1. Duplicate & Supersession Phase
    amended_ids: Set[str] = set()
    for e in events:
        if e.linked_event_id and e.linked_event_id in event_by_id:
            original = event_by_id[e.linked_event_id]
            
            # If this is a duplicate marker, just mark the current event as duplicate
            if e.status == EventStatus.DUPLICATE:
                continue
                
            # If original was cancelled/failed, and this is the retry/settlement, original stays cancelled
            if original.status in EventLifecycle.NON_CASH_STATUSES:
                amended_ids.add(e.linked_event_id)
                resolutions[e.linked_event_id] = f"superseded_by_retry_{e.event_id}"
                
            # If original was pending/initiated and this is settled/confirmed, amend original
            elif original.status in [EventStatus.PENDING, EventStatus.INITIATED] and e.status in EventLifecycle.REALIZED_STATUSES:
                amended_ids.add(e.linked_event_id)
                resolutions[e.linked_event_id] = f"settled_as_{e.event_id}"
                
            # If this is an explicit amendment
            elif e.status == EventStatus.AMENDED:
                amended_ids.add(e.linked_event_id)
                resolutions[e.linked_event_id] = f"amended_by_{e.event_id}"
                # e itself replaces original, but e's status should be treated as confirmed
                e.status = EventStatus.CONFIRMED

    # 2. Message Extraction Amendment Phase
    # (Leaving placeholder for Phase 9 Evidence Extraction. For now we skip modifying events via messages 
    # unless they are explicitly passed as amendments).
    
    # 3. Inclusion & FX Phase
    included = []
    for event in events:
        eid = event.event_id
        
        is_amended = eid in amended_ids
        if is_amended:
            resolutions[eid] = resolutions.get(eid, "amended")
            continue
            
        if EventLifecycle.should_include(event):
            # FX Conversion
            if event.amount is not None and event.currency != profile.home_currency:
                effective_date = event.settlement_date or event.event_date or request_date
                try:
                    converted = fx.to_home_currency(
                        amount=event.amount,
                        from_currency=event.currency,
                        to_currency=profile.home_currency,
                        date_str=str(effective_date)
                    )
                    event.amount_home_currency = converted
                except Exception as e:
                    logger.error(f"FX failure for {eid}: {e}")
                    event.amount_home_currency = None
            else:
                event.amount_home_currency = event.amount
                
            included.append(event)
            resolutions[eid] = "included"
        else:
            resolutions[eid] = resolutions.get(eid, f"excluded_status_{event.status}")
            
    return included, resolutions
