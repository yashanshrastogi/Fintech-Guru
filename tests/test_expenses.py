from decimal import Decimal
from forecasting.expenses import project_expense_amount

def test_stable_expenses_use_median():
    # Mean = 100, std = 0 (0% of mean). Median = 100
    amounts = [Decimal("100"), Decimal("100"), Decimal("100")]
    assert project_expense_amount(amounts) == Decimal("100.00")

    # Small variance: 95, 100, 105. 
    # Mean = 100, std = 5 (5% of mean). Median = 100
    amounts = [Decimal("95"), Decimal("100"), Decimal("105")]
    assert project_expense_amount(amounts) == Decimal("100.00")

def test_variable_expenses_use_p90():
    # High variance: electricity bills in summer/winter.
    # 50, 60, 200, 210.
    # Mean = 130, std = ~88. (67% of mean). 
    # Median = 130. 
    # P90 of [50, 60, 200, 210] = 207.0
    amounts = [Decimal("50"), Decimal("60"), Decimal("200"), Decimal("210")]
    projected = project_expense_amount(amounts)
    # The P90 provides a much safer buffer than the 130 median
    assert projected == Decimal("207.00")

def test_edge_cases():
    assert project_expense_amount([]) == Decimal("0")
    assert project_expense_amount([Decimal("42.50")]) == Decimal("42.50")
