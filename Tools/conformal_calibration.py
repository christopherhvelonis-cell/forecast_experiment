import numpy as np
import pandas as pd

def split_conformal_intervals(residuals: pd.Series, alpha: float = 0.1) -> float:
    """Return q-hat to widen intervals to (1-alpha) coverage. Placeholder."""
    return float(residuals.abs().quantile(1 - alpha))

def enbpi_adjustment(residuals: pd.Series, alpha: float = 0.1) -> float:
    """Sequential EnbPI placeholder: use split-conformal as proxy."""
    return split_conformal_intervals(residuals, alpha)
