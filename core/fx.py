"""
FX (Foreign Exchange) conversion using fixed dated rates from exchange_rates.csv.
Never uses live rates. Only uses supplied static rates.
"""
from decimal import Decimal
from datetime import date
from typing import Dict, Optional, Tuple
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class FXConverter:
    """
    Converts currency amounts using fixed dated rates.
    Rates are looked up by (from_currency, to_currency, date).
    If exact date not found, uses the nearest available rate on or before the date.
    """
    
    def __init__(self, exchange_rates_df: pd.DataFrame):
        self._rates: Dict[Tuple[str, str, date], Decimal] = {}
        self._rate_dates: Dict[Tuple[str, str], list] = {}  # sorted list of available dates
        self._load_rates(exchange_rates_df)
    
    def _load_rates(self, df: pd.DataFrame):
        """Load all rates into memory, indexed for fast lookup."""
        for _, row in df.iterrows():
            rate_date = pd.to_datetime(row['rate_date']).date()
            from_cur = str(row['from_currency']).strip()
            to_cur = str(row['to_currency']).strip()
            rate = Decimal(str(row['rate']))
            
            self._rates[(from_cur, to_cur, rate_date)] = rate
            key = (from_cur, to_cur)
            if key not in self._rate_dates:
                self._rate_dates[key] = []
            self._rate_dates[key].append(rate_date)
        
        # Sort date lists
        for key in self._rate_dates:
            self._rate_dates[key].sort()
        
        # Build derived rates (invert and chain)
        self._build_derived_rates()
    
    def _build_derived_rates(self):
        """Build derived rates from existing ones (A→C via A→B and B→C)."""
        # First collect all existing pairs and their dates
        existing = list(self._rates.items())
        
        # Add inverse rates
        inverse_to_add = {}
        for (from_cur, to_cur, rate_date), rate in existing:
            inv_key = (to_cur, from_cur, rate_date)
            if inv_key not in self._rates:
                inverse_to_add[inv_key] = Decimal("1") / rate
        
        for key, rate in inverse_to_add.items():
            self._rates[key] = rate
            pair_key = (key[0], key[1])
            if pair_key not in self._rate_dates:
                self._rate_dates[pair_key] = []
            if key[2] not in self._rate_dates[pair_key]:
                self._rate_dates[pair_key].append(key[2])
                self._rate_dates[pair_key].sort()
        
        # Add chained rates (e.g. USD→INR via USD→EUR and EUR→INR is not needed
        # but USD→IDR, USD→ZAR etc. via USD→EUR→ZAR if direct not available)
        # The dataset provides: EUR/ZAR, USD/EUR, USD/IDR, USD/INR
        # Derive: EUR/IDR, EUR/INR, ZAR/USD, etc.
        all_currencies = set()
        for (from_cur, to_cur, _) in list(self._rates.keys()):
            all_currencies.add(from_cur)
            all_currencies.add(to_cur)
        
        # Collect all dates
        all_dates = set()
        for dates in self._rate_dates.values():
            all_dates.update(dates)
        
        # Chain through USD as pivot for any missing pair
        currencies = list(all_currencies)
        for d in all_dates:
            for c1 in currencies:
                for c2 in currencies:
                    if c1 == c2:
                        continue
                    if (c1, c2, d) in self._rates:
                        continue
                    # Try via USD
                    if (c1, "USD", d) in self._rates and ("USD", c2, d) in self._rates:
                        chained = self._rates[(c1, "USD", d)] * self._rates[("USD", c2, d)]
                        self._rates[(c1, c2, d)] = chained
                        pair_key = (c1, c2)
                        if pair_key not in self._rate_dates:
                            self._rate_dates[pair_key] = []
                        if d not in self._rate_dates[pair_key]:
                            self._rate_dates[pair_key].append(d)
                            self._rate_dates[pair_key].sort()
    
    def _find_best_rate_date(self, from_cur: str, to_cur: str, lookup_date: date) -> Optional[date]:
        """Find the best available rate date on or before lookup_date."""
        key = (from_cur, to_cur)
        if key not in self._rate_dates:
            return None
        dates = self._rate_dates[key]
        # Find latest date <= lookup_date
        best = None
        for d in dates:
            if d <= lookup_date:
                best = d
            else:
                break
        if best is None and dates:
            # Use earliest available date (for very old dates)
            best = dates[0]
        return best
    
    def convert(self, amount: Decimal, from_currency: str, to_currency: str, 
                as_of_date: date) -> Optional[Decimal]:
        """
        Convert amount from from_currency to to_currency using the rate
        available on or before as_of_date.
        Returns None if conversion is not possible.
        """
        if from_currency == to_currency:
            return amount
        
        if amount is None:
            return None
        
        # Try direct rate
        best_date = self._find_best_rate_date(from_currency, to_currency, as_of_date)
        if best_date is not None:
            rate = self._rates.get((from_currency, to_currency, best_date))
            if rate is not None:
                return amount * rate
        
        logger.warning(f"No FX rate found: {from_currency}→{to_currency} as of {as_of_date}")
        return None
    
    def to_home_currency(self, amount: Decimal, currency: str, home_currency: str,
                          as_of_date: date) -> Optional[Decimal]:
        """Convert amount to home currency."""
        if currency == home_currency:
            return amount
        return self.convert(amount, currency, home_currency, as_of_date)


_fx_instance: Optional[FXConverter] = None


def get_fx_converter(exchange_rates_df: pd.DataFrame = None) -> FXConverter:
    """Get or create the global FX converter."""
    global _fx_instance
    if _fx_instance is None and exchange_rates_df is not None:
        _fx_instance = FXConverter(exchange_rates_df)
    return _fx_instance
