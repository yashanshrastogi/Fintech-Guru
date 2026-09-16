import statistics
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
from typing import List

def project_expense_amount(amounts: List[Decimal]) -> Decimal:
    """
    Project the future recurring expense amount based on historical amounts.
    If the standard deviation is high (> 15% of the mean), use the 90th percentile
    to build a conservative safety buffer. Otherwise, use the median.
    
    Args:
        amounts: List of historical expense amounts.
        
    Returns:
        The projected conservative amount for the next billing cycle.
    """
    if not amounts:
        return Decimal("0")
        
    if len(amounts) < 2:
        return amounts[0]
        
    float_amounts = [float(a) for a in amounts]
    mean_val = statistics.mean(float_amounts)
    std_val = statistics.stdev(float_amounts)
    median_val = statistics.median(float_amounts)
    
    # If standard deviation is greater than 15% of the mean, the expense is highly variable
    if mean_val > 0 and (std_val / mean_val) > 0.15:
        # Use 90th percentile for safety buffer
        p90 = np.percentile(float_amounts, 90)
        return Decimal(str(p90)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Otherwise, median is robust
    return Decimal(str(median_val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
