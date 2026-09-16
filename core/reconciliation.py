from enum import Enum
from typing import List, Dict, Set, Tuple
from decimal import Decimal
import logging
from datetime import date

from core.models import BaseEvent, UserProfile

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
    def should_include(event: BaseEvent, is_amended: bool = False) -> bool:
        """Determines if an event should be included in cashflow forecasting."""
        if is_amended or event.status in EventLifecycle.NON_CASH_STATUSES:
            return False
            
        # Unrealized investment credits are not liquid cash
        if event.category == "investment" and getattr(event, "event_type", "") == "income":
            return False
            
        # Pending credits (income) are not trusted until settled/confirmed
        if event.status == EventStatus.PENDING and getattr(event, "event_type", "") == "income":
            return False
            
        # Pending debits (expenses) ARE included to be conservative with cash
        if event.status == EventStatus.PENDING and getattr(event, "event_type", "") == "expense":
            return True
            
        if event.status in EventLifecycle.REALIZED_STATUSES:
            return True
            
        # Initiated behaves like pending
        if event.status == EventStatus.INITIATED and getattr(event, "event_type", "") == "expense":
            return True
            
        return False

def reconcile_events(
    events: List[BaseEvent],
    profile: UserProfile,
    request_date: date,
) -> Tuple[List[BaseEvent], Dict[str, str]]:
    """
    Reconcile financial events using deterministic precedence rules.
    Returns:
    - List of events to include in cash flow
    - Dict of event_id -> resolution reason (for audit)
    """
    resolutions: Dict[str, str] = {}
    
    unique_events = []
    seen_ids = set()
    for e in events:
        if e.event_id not in seen_ids:
            unique_events.append(e)
            seen_ids.add(e.event_id)
        else:
            resolutions[e.event_id] = "duplicate_id_removed"
            
    events = unique_events
    event_by_id: Dict[str, BaseEvent] = {e.event_id: e for e in events}
    
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

    # 3. Inclusion Phase
    included = []
    for event in events:
        eid = event.event_id
        
        is_amended = eid in amended_ids
        if is_amended:
            resolutions[eid] = resolutions.get(eid, "amended")
            continue
            
        if EventLifecycle.should_include(event):
            included.append(event)
            resolutions[eid] = "included"
        else:
            resolutions[eid] = resolutions.get(eid, f"excluded_status_{event.status}")
            
    return included, resolutions
