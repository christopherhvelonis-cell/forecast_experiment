import numpy as np, pandas as pd
def psis_loo_weights(log_scores: pd.DataFrame) -> pd.Series:
    x = log_scores.mean(0).to_numpy(); x = x - x.max()
    w = np.exp(x); w = w / w.sum()
    return pd.Series(w, index=log_scores.columns)
