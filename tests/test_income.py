import pytest
from datetime import date
from forecasting.income import project_next_salary_date

def test_salary_projection_same_month():
    # Paid on 15th, requesting on 10th. Next is 15th of same month.
    assert project_next_salary_date(date(2026, 8, 15), 15, date(2026, 9, 10)) == date(2026, 9, 15)

def test_salary_projection_next_month():
    # Requesting on 16th. Next is 15th of next month.
    assert project_next_salary_date(date(2026, 8, 15), 15, date(2026, 9, 16)) == date(2026, 10, 15)

def test_salary_projection_end_of_month_leap_year():
    # Typical DOM is 31.
    # In Feb 2028 (leap year), it should cap at 29th.
    assert project_next_salary_date(date(2028, 1, 31), 31, date(2028, 2, 1)) == date(2028, 2, 29)

def test_salary_projection_end_of_month_non_leap():
    # Typical DOM is 31.
    # In Feb 2026 (non-leap year), it should cap at 28th.
    assert project_next_salary_date(date(2026, 1, 31), 31, date(2026, 2, 1)) == date(2026, 2, 28)

def test_salary_projection_ignores_weekend_shifted_last_date():
    # Last month the 15th was a Sunday, so user got paid on the 13th (Friday).
    # Typical DOM is still 15. The next projection MUST still be the 15th.
    assert project_next_salary_date(date(2026, 8, 13), 15, date(2026, 9, 1)) == date(2026, 9, 15)

def test_invalid_dom():
    with pytest.raises(ValueError):
        project_next_salary_date(date(2026, 8, 15), 32, date(2026, 9, 10))
