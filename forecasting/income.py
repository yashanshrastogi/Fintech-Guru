import calendar
from datetime import date, timedelta
from typing import Optional

def project_next_salary_date(last_date: date, typical_dom: int, current_date: date) -> Optional[date]:
    """
    Project the next salary date strictly anchored to the typical day of the month,
    even if the previous month shifted due to a weekend.
    
    Args:
        last_date: Date of the last recorded salary event.
        typical_dom: The anchored typical day of the month (e.g., 15).
        current_date: The date from which to project forward.
        
    Returns:
        The next projected salary date that is > current_date.
    """
    if typical_dom < 1 or typical_dom > 31:
        raise ValueError("typical_dom must be between 1 and 31")

    # Start looking in the same month as current_date
    year = current_date.year
    month = current_date.month
    
    # We will search up to 3 months forward
    for _ in range(3):
        max_day = calendar.monthrange(year, month)[1]
        target_day = min(typical_dom, max_day)
        
        target_date = date(year, month, target_day)
        
        # Must be strictly after current_date
        if target_date > current_date:
            return target_date
            
        # Move to next month
        month += 1
        if month > 12:
            month = 1
            year += 1
            
    return None
