"""
Data loader for all CSV files. Loads and indexes data for efficient lookup.
All CSVs are loaded once and cached in memory.
"""
from decimal import Decimal
from datetime import date
from typing import Dict, List, Optional
from pathlib import Path
import pandas as pd
import logging

from config import (
    FINANCIAL_PROFILES_CSV, FINANCIAL_EVENTS_CSV, EXCHANGE_RATES_CSV,
    PAYMENT_OPTIONS_CSV, MESSAGES_CSV, IMAGES_CSV, REQUESTS_CSV, SAMPLE_REQUESTS_CSV
)
from models import (
    FinancialProfile, FinancialEvent, PaymentOption, Request,
    MessageEvidence, ImageEvidence, to_decimal
)

logger = logging.getLogger(__name__)


class DataStore:
    """Central data store with all loaded and indexed data."""
    
    def __init__(self):
        self.profiles: Dict[str, FinancialProfile] = {}
        self.events_by_user: Dict[str, List[FinancialEvent]] = {}
        self.events_by_id: Dict[str, FinancialEvent] = {}
        self.payment_options_by_request: Dict[str, List[PaymentOption]] = {}
        self.messages_by_user: Dict[str, List[MessageEvidence]] = {}
        self.messages_by_request: Dict[str, List[MessageEvidence]] = {}
        self.messages_by_event: Dict[str, List[MessageEvidence]] = {}
        self.images_by_event: Dict[str, ImageEvidence] = {}
        self.images_by_request: Dict[str, ImageEvidence] = {}
        self.exchange_rates_df: pd.DataFrame = None
        self.requests: List[Request] = []
        self.sample_requests: List[Request] = []
        self.sample_outputs: Dict[str, dict] = {}


def _parse_pipe_list(value: str) -> List[str]:
    """Parse a pipe-separated list, returning empty list if blank."""
    if pd.isna(value) or str(value).strip() == "":
        return []
    return [v.strip() for v in str(value).split("|") if v.strip()]


def _parse_date(value) -> Optional[date]:
    """Parse a date string to date object."""
    if pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return pd.to_datetime(str(value).strip()).date()
    except Exception:
        return None


def _parse_bool(value) -> bool:
    """Parse a boolean value."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    return bool(value)


def load_all_data() -> DataStore:
    """Load all CSV files and return a populated DataStore."""
    store = DataStore()
    
    logger.info("Loading exchange rates...")
    store.exchange_rates_df = pd.read_csv(EXCHANGE_RATES_CSV)
    
    logger.info("Loading financial profiles...")
    _load_profiles(store)
    
    logger.info("Loading financial events...")
    _load_events(store)
    
    logger.info("Loading payment options...")
    _load_payment_options(store)
    
    logger.info("Loading messages...")
    _load_messages(store)
    
    logger.info("Loading images...")
    _load_images(store)
    
    logger.info("Loading requests...")
    _load_requests(store)
    
    logger.info("Loading sample requests...")
    _load_sample_requests(store)
    
    logger.info(f"Data loaded: {len(store.profiles)} profiles, "
                f"{sum(len(v) for v in store.events_by_user.values())} events, "
                f"{len(store.requests)} requests")
    
    return store


def _load_profiles(store: DataStore):
    df = pd.read_csv(FINANCIAL_PROFILES_CSV)
    for _, row in df.iterrows():
        uid = str(row['user_id']).strip()
        
        max_months = None
        if not pd.isna(row.get('max_installment_months', '')):
            val = row['max_installment_months']
            if str(val).strip() != "":
                try:
                    max_months = int(val)
                except Exception:
                    pass
        
        profile = FinancialProfile(
            user_id=uid,
            home_currency=str(row['home_currency']).strip(),
            current_available_balance=Decimal(str(row['current_available_balance'])),
            minimum_balance_to_keep=Decimal(str(row['minimum_balance_to_keep'])),
            financial_priorities=_parse_pipe_list(row.get('financial_priorities', '')),
            expense_categories_to_protect=_parse_pipe_list(row.get('expense_categories_to_protect', '')),
            expense_categories_willing_to_reduce=_parse_pipe_list(row.get('expense_categories_user_is_willing_to_reduce', '')),
            expense_categories_willing_to_stop=_parse_pipe_list(row.get('expense_categories_user_is_willing_to_stop', '')),
            payment_methods_user_will_consider=_parse_pipe_list(row.get('payment_methods_user_will_consider', '')),
            max_installment_months=max_months,
        )
        store.profiles[uid] = profile


def _load_events(store: DataStore):
    df = pd.read_csv(FINANCIAL_EVENTS_CSV, low_memory=False)
    
    for _, row in df.iterrows():
        uid = str(row['user_id']).strip()
        eid = str(row['event_id']).strip()
        
        # Parse amount (may be blank)
        amount_raw = row.get('amount', '')
        amount = None
        if not pd.isna(amount_raw) and str(amount_raw).strip() != "":
            try:
                amount = Decimal(str(amount_raw).strip())
            except Exception:
                pass
        
        event = FinancialEvent(
            event_id=eid,
            user_id=uid,
            event_type=str(row.get('event_type', '')).strip(),
            description=str(row.get('description', '')).strip(),
            category=str(row.get('category', '')).strip(),
            direction=str(row.get('direction', '')).strip(),
            amount=amount,
            currency=str(row.get('currency', '')).strip(),
            event_date=_parse_date(row.get('event_date')),
            settlement_date=_parse_date(row.get('settlement_date')),
            status=str(row.get('status', '')).strip(),
            linked_event_id=str(row['linked_event_id']).strip() if not pd.isna(row.get('linked_event_id', float('nan'))) and str(row.get('linked_event_id', '')).strip() else None,
            flexibility=str(row.get('flexibility', 'fixed')).strip(),
            minimum_allowed_amount=to_decimal(row.get('minimum_allowed_amount')),
        )
        
        store.events_by_id[eid] = event
        if uid not in store.events_by_user:
            store.events_by_user[uid] = []
        store.events_by_user[uid].append(event)


def _load_payment_options(store: DataStore):
    df = pd.read_csv(PAYMENT_OPTIONS_CSV)
    
    for _, row in df.iterrows():
        rid = str(row['request_id']).strip()
        
        freq_days = None
        if not pd.isna(row.get('payment_frequency_days', float('nan'))):
            val = str(row['payment_frequency_days']).strip()
            if val and val != 'nan':
                try:
                    freq_days = int(float(val))
                except Exception:
                    pass
        
        opt = PaymentOption(
            payment_option_id=str(row['payment_option_id']).strip(),
            request_id=rid,
            payment_method=str(row['payment_method']).strip(),
            payment_amount=Decimal(str(row['payment_amount'])),
            number_of_payments=int(row['number_of_payments']),
            first_payment_date=_parse_date(row['first_payment_date']),
            payment_frequency_days=freq_days,
            financing_fee=Decimal(str(row.get('financing_fee', '0') or '0')),
            total_payable_amount=Decimal(str(row['total_payable_amount'])),
        )
        
        if rid not in store.payment_options_by_request:
            store.payment_options_by_request[rid] = []
        store.payment_options_by_request[rid].append(opt)


def _load_messages(store: DataStore):
    df = pd.read_csv(MESSAGES_CSV)
    
    for _, row in df.iterrows():
        uid = str(row.get('user_id', '')).strip()
        rid = str(row.get('request_id', '')).strip() if not pd.isna(row.get('request_id', float('nan'))) else None
        eid = str(row.get('related_event_id', '')).strip() if not pd.isna(row.get('related_event_id', float('nan'))) else None
        
        msg = MessageEvidence(
            message_id=str(row['message_id']).strip(),
            user_id=uid,
            request_id=rid if rid else None,
            related_event_id=eid if eid else None,
            sent_at=str(row.get('sent_at', '')).strip(),
            source_type=str(row.get('source_type', '')).strip(),
            message_text=str(row.get('message_text', '')).strip(),
        )
        
        if uid not in store.messages_by_user:
            store.messages_by_user[uid] = []
        store.messages_by_user[uid].append(msg)
        
        if rid:
            if rid not in store.messages_by_request:
                store.messages_by_request[rid] = []
            store.messages_by_request[rid].append(msg)
        
        if eid:
            if eid not in store.messages_by_event:
                store.messages_by_event[eid] = []
            store.messages_by_event[eid].append(msg)


def _load_images(store: DataStore):
    df = pd.read_csv(IMAGES_CSV)
    
    for _, row in df.iterrows():
        uid = str(row.get('user_id', '')).strip()
        rid = str(row.get('request_id', '')).strip() if not pd.isna(row.get('request_id', float('nan'))) else None
        eid = str(row.get('related_event_id', '')).strip() if not pd.isna(row.get('related_event_id', float('nan'))) else None
        img_id = str(row['image_id']).strip()
        
        img = ImageEvidence(
            image_id=img_id,
            user_id=uid,
            request_id=rid if rid else None,
            related_event_id=eid if eid else None,
        )
        
        if eid:
            store.images_by_event[eid] = img
        if rid:
            store.images_by_request[rid] = img


def _load_requests_from_df(df: pd.DataFrame) -> List[Request]:
    requests = []
    for _, row in df.iterrows():
        req = Request(
            request_id=str(row['request_id']).strip(),
            user_id=str(row['user_id']).strip(),
            request_date=_parse_date(row['request_date']),
            request_type=str(row.get('request_type', '')).strip(),
            requested_amount=Decimal(str(row['requested_amount'])),
            desired_completion_date=_parse_date(row['desired_completion_date']),
            allows_partial_payment=_parse_bool(row.get('allows_partial_payment', False)),
            request_text=str(row.get('request_text', '')).strip(),
        )
        requests.append(req)
    return requests


def _load_requests(store: DataStore):
    df = pd.read_csv(REQUESTS_CSV)
    store.requests = _load_requests_from_df(df)


def _load_sample_requests(store: DataStore):
    df = pd.read_csv(SAMPLE_REQUESTS_CSV)
    store.sample_requests = _load_requests_from_df(df)
    
    # Load sample outputs
    output_cols = ['amount_safe_to_pay', 'affordability_status', 'recommended_payment_method',
                   'payment_plan', 'earliest_date_for_full_payment', 'spending_changes_needed',
                   'decision_explanation']
    for _, row in df.iterrows():
        rid = str(row['request_id']).strip()
        store.sample_outputs[rid] = {col: row.get(col, '') for col in output_cols if col in df.columns}
