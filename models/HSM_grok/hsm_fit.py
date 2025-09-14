import pandas as pd
import numpy as np
from statsmodels.tsa.statespace.kalman_filter import KalmanFilter
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

# Load data
data = pd.concat([
    pd.read_csv('data/processed/mass_public_polarization.csv')[['year', 'affective_polarization']],
    pd.read_csv('data/processed/public-trust-in-government.csv')[['Year', 'public_trust_government']],
    pd.read_csv('data/processed/vep_turnout_pct.csv').query('indicator == "vep_turnout_pres_pct"')[['year', 'value']],
    # Add other indicators
], axis=1).dropna(subset=['year']).set_index('year')
data.columns = ['polarization', 'trust', 'turnout', ...]

# Handle breaks (from annotations.md)
breaks = {'real_gdp_growth': 2015, ...}  # Example: year 2015 for GDP break
regimes = np.where(data.index < breaks.get('real_gdp_growth', np.inf), 0, 1)

# State-space model
model = KalmanFilter(
    endog=data,
    k_states=6,  # 2 per indicator (level, trend) for 3 key indicators
    transition=[[1, 1, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0], ...],  # Level + trend dynamics
    observation=[[1, 0, 1, 0, 1, 0], ...],  # Map states to indicators
    state_cov=np.diag([0.1, 0.01, 0.1, 0.01, 0.1, 0.01]),  # Initial variances
)
results = model.fit()

# Regime-switching for breaks
regime_model = MarkovRegression(data, k_regimes=2, exog=regimes).fit()

# Forecast 1–15 years, scenarios to 2065
forecasts = []
for origin in [1985, 1990, ..., 2020]:
    train = data.loc[:origin]
    model.fit(train)
    pred = model.forecast(40)  # Quantiles 5/50/95
    forecasts.append(pred)

# Event probabilities (trust_below_20, turnout_above_65)
event_probs = {
    'trust_below_20': (pred['trust'] < 20).mean(axis=1),
    'turnout_above_65': (pred['turnout'] >= 65).mean(axis=1),
}

# ECC post-processing
from statsmodels.distributions.copula import GaussianCopula
copula = GaussianCopula(corr=data.corr())
pred_joint = copula.sample(pred, n=10000)

# Save outputs
pd.DataFrame(forecasts, columns=['year', 'polarization_q05', 'polarization_q50', ...]).to_csv('models/HSM_grok/predictions.csv')
pd.DataFrame(event_probs).to_csv('models/HSM_grok/event_probs.csv')