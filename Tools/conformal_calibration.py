import pandas as pd
def split_conformal_intervals(residuals: pd.Series, alpha: float = 0.1) -> float:
    return float(residuals.abs().quantile(1 - alpha))
def enbpi_adjustment(residuals: pd.Series, alpha: float = 0.1) -> float:
    return split_conformal_intervals(residuals, alpha)
