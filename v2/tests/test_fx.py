"""
V2 Regression Tests — FX Conversion (Phase 4).

Tests correct FX date selection for different event types.
Run with: pytest v2/tests/test_fx.py -v
"""
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date
import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "code"))

from conftest import make_event


# ---------------------------------------------------------------------------
# Helper: Build a minimal FXConverter from synthetic rates
# ---------------------------------------------------------------------------

def make_fx_converter():
    """Build FXConverter with synthetic USD/IDR rates on two dates."""
    import pandas as pd
    from fx import FXConverter

    data = [
        # event date
        {"rate_date": "2026-06-01", "from_currency": "USD", "to_currency": "IDR", "rate": 15000},
        {"rate_date": "2026-06-01", "from_currency": "IDR", "to_currency": "USD", "rate": 1 / 15000},
        # request date (different rate)
        {"rate_date": "2026-09-01", "from_currency": "USD", "to_currency": "IDR", "rate": 16000},
        {"rate_date": "2026-09-01", "from_currency": "IDR", "to_currency": "USD", "rate": 1 / 16000},
    ]
    df = pd.DataFrame(data)
    return FXConverter(df)


# ---------------------------------------------------------------------------
# 1. Same currency — no conversion needed
# ---------------------------------------------------------------------------

def test_same_currency_no_conversion():
    from fx import FXConverter
    import pandas as pd

    df = pd.DataFrame([
        {"rate_date": "2026-09-01", "from_currency": "USD", "to_currency": "IDR", "rate": 16000},
    ])
    fx = FXConverter(df)

    result = fx.to_home_currency(Decimal("100"), "IDR", "IDR", date(2026, 9, 1))
    assert result == Decimal("100"), "Same-currency conversion must return original amount unchanged"


# ---------------------------------------------------------------------------
# 2. Foreign currency cash event uses settlement/event date rate
# ---------------------------------------------------------------------------

def test_foreign_cash_event_uses_event_date_rate():
    """A USD expense that settled on 2026-06-01 should use the June rate (15000)."""
    from reconciliation import _get_fx_date

    event = make_event(
        event_id="evt_fx_cash",
        category="rent",
        direction="debit",
        amount=Decimal("100"),
        currency="USD",
        event_date=date(2026, 6, 1),
        settlement_date=None,
        event_type="expense",
    )

    fx_date = _get_fx_date(event, request_date=date(2026, 9, 1))
    assert fx_date == date(2026, 6, 1), f"Cash event must use event_date, got {fx_date}"

    fx = make_fx_converter()
    converted = fx.to_home_currency(Decimal("100"), "USD", "IDR", fx_date)
    assert converted == Decimal("1500000"), f"Expected 100 * 15000 = 1500000, got {converted}"


# ---------------------------------------------------------------------------
# 3. Investment credit uses request_date rate (mark-to-market)
# ---------------------------------------------------------------------------

def test_investment_credit_uses_request_date_rate():
    """A USD investment credit from June should be valued at Sept rate (16000)."""
    from reconciliation import _get_fx_date

    event = make_event(
        event_id="evt_investment",
        category="investment",
        direction="credit",
        amount=Decimal("100"),
        currency="USD",
        event_date=date(2026, 6, 1),
        settlement_date=None,
        event_type="investment",
    )

    fx_date = _get_fx_date(event, request_date=date(2026, 9, 1))
    assert fx_date == date(2026, 9, 1), f"Investment credit must use request_date, got {fx_date}"

    fx = make_fx_converter()
    converted = fx.to_home_currency(Decimal("100"), "USD", "IDR", fx_date)
    assert converted == Decimal("1600000"), f"Expected 100 * 16000 = 1600000, got {converted}"


# ---------------------------------------------------------------------------
# 4. Investment debit (cash invested) uses event date
# ---------------------------------------------------------------------------

def test_investment_debit_uses_event_date():
    """When cash is invested (debit), use the event date for FX — it was a real cash outflow."""
    from reconciliation import _get_fx_date

    event = make_event(
        event_id="evt_invest_debit",
        category="investment",
        direction="debit",
        amount=Decimal("100"),
        currency="USD",
        event_date=date(2026, 6, 1),
        event_type="investment",
    )

    fx_date = _get_fx_date(event, request_date=date(2026, 9, 1))
    assert fx_date == date(2026, 6, 1), f"Investment debit must use event_date, got {fx_date}"


# ---------------------------------------------------------------------------
# 5. Settlement date takes priority over event date for cash events
# ---------------------------------------------------------------------------

def test_settlement_date_priority_over_event_date():
    """If settlement_date is set, use it (not event_date) for FX lookup."""
    from reconciliation import _get_fx_date

    event = make_event(
        event_id="evt_settled",
        category="expense",
        direction="debit",
        amount=Decimal("100"),
        currency="USD",
        event_date=date(2026, 6, 1),   # event created in June
        settlement_date=date(2026, 9, 1),  # but actually settled in Sept
        event_type="expense",
    )

    fx_date = _get_fx_date(event, request_date=date(2026, 9, 1))
    assert fx_date == date(2026, 9, 1), f"Settlement date must take priority, got {fx_date}"


# ---------------------------------------------------------------------------
# 6. Missing FX rate returns None (not zero, not error)
# ---------------------------------------------------------------------------

def test_missing_fx_rate_returns_none():
    """If no rate is available for a currency pair, conversion must return None."""
    import pandas as pd
    from fx import FXConverter

    df = pd.DataFrame([
        # Only USD/IDR rate available
        {"rate_date": "2026-09-01", "from_currency": "USD", "to_currency": "IDR", "rate": 16000},
    ])
    fx = FXConverter(df)

    # Try converting ZAR → IDR (not in the table, and no pivot available)
    result = fx.to_home_currency(Decimal("100"), "ZAR", "INR", date(2026, 9, 1))
    assert result is None, f"Missing FX rate must return None, got {result}"


# ---------------------------------------------------------------------------
# 7. Chained rate via USD pivot works
# ---------------------------------------------------------------------------

def test_chained_rate_via_usd_pivot():
    """IDR→ZAR should work via IDR→USD→ZAR chain."""
    import pandas as pd
    from fx import FXConverter

    data = [
        {"rate_date": "2026-09-01", "from_currency": "USD", "to_currency": "IDR", "rate": 16000},
        {"rate_date": "2026-09-01", "from_currency": "IDR", "to_currency": "USD", "rate": 1/16000},
        {"rate_date": "2026-09-01", "from_currency": "USD", "to_currency": "ZAR", "rate": 18},
        {"rate_date": "2026-09-01", "from_currency": "ZAR", "to_currency": "USD", "rate": 1/18},
    ]
    fx = FXConverter(pd.DataFrame(data))

    # 16000 IDR → 1 USD → 18 ZAR
    result = fx.convert(Decimal("16000"), "IDR", "ZAR", date(2026, 9, 1))
    assert result is not None
    assert abs(result - Decimal("18")) < Decimal("0.01"), f"Expected ~18 ZAR, got {result}"
