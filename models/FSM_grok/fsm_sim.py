import pandas as pd
import numpy as np
from scipy.stats import t, poisson
from statsmodels.distributions.copula import GaussianCopula

# Load data
data = pd.concat([
    pd.read_csv('data/processed/mass_public_polarization.csv')[['year', 'affective_polarization']],
    pd.read_csv('data/processed/public-trust-in-government.csv')[['Year', 'public_trust_government']],
    pd.read_csv('data/processed/vep_turnout_pct.csv').query('indicator == "vep_turnout_pres_pct"')[['year', 'value']],
], axis=1).dropna(subset=['year']).set_index('year')
data.columns = ['polarization', 'trust', 'turnout']

# Estimate drifts and volatilities
drifts = data.diff().mean()  # e.g., trust: -0.5%/year
volatilities = data.diff().std()

# Simulate 10,000 paths to 2065
n_paths = 10000
horizon = 40
paths = np.zeros((horizon, len(data.columns), n_paths))
last_observed = data.loc[2024]
for t in range(horizon):
    # Local level with drift
    paths[t] = last_observed + drifts + np.random.normal(0, volatilities, (len(data.columns), n_paths))
    # Add shocks (Poisson, t-distributed)
    shock_events = poisson.rvs(0.1, size=(len(data.columns), n_paths))
    shock_magnitudes = t.rvs(df=5, scale=volatilities, size=(len(data.columns), n_paths))
    paths[t] += shock_events * shock_magnitudes
    last_observed = paths[t]

# Event probabilities
event_probs = {
    'trust_below_20': (paths[:, 1, :] < 20).mean(axis=1),
    'turnout_above_65': (paths[:, 2, :] >= 65).mean(axis=1),
    'polarization_above_50': (paths[:, 0, :] > 50).mean(axis=1),
}

# ECC post-processing
copula = GaussianCopula(corr=data.corr())
paths_joint = copula.sample(paths, n=n_paths)

# Save outputs
quantiles = np.percentile(paths_joint, [5, 50, 95], axis=2)
pd.DataFrame({
    'year': range(2026, 2066),
    'polarization_q05': quantiles[0, :, 0], 'polarization_q50': quantiles[1, :, 0], 'polarization_q95': quantiles[2, :, 0],
    'trust_q05': quantiles[0, :, 1], 'trust_q50': quantiles[1, :, 1], 'trust_q95': quantiles[2, :, 1],
    'turnout_q05': quantiles[0, :, 2], 'turnout_q50': quantiles[1, :, 2], 'turnout_q95': quantiles[2, :, 2],
}).to_csv('models/FSM_grok/scenarios.csv')
pd.DataFrame(event_probs).to_csv('models/FSM_grok/event_probs.csv')