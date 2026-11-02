| Study | Forecast | Mean latent-loss rank | Central 90% coverage | Mean sample-mean mismatch | Seeds |
|---|---|---:|---:|---:|---:|
| holdout_accelerating | drift_u | 0.654 | 57.5% | 0.031 | 40 |
| holdout_accelerating | pseudo_bma | 0.654 | 57.5% | 0.031 | 40 |
| holdout_accelerating | stacked | 0.714 | 62.5% | 0.038 | 40 |
| holdout_accelerating | trend | 0.990 | 2.5% | 0.000 | 40 |
| holdout_lane_split | drift_u | 1.000 | 0.0% | 0.017 | 40 |
| holdout_lane_split | pseudo_bma | 1.000 | 0.0% | 0.009 | 40 |
| holdout_lane_split | stacked | 1.000 | 0.0% | 0.015 | 40 |
| holdout_lane_split | trend | 0.995 | 0.0% | 0.000 | 40 |
| holdout_random_switch | drift_u | 0.674 | 42.5% | 0.053 | 40 |
| holdout_random_switch | pseudo_bma | 0.765 | 25.0% | 0.022 | 40 |
| holdout_random_switch | stacked | 0.720 | 50.0% | 0.046 | 40 |
| holdout_random_switch | trend | 0.809 | 32.5% | 0.000 | 40 |
| holdout_random_walk | drift_u | 0.227 | 20.0% | 0.055 | 40 |
| holdout_random_walk | pseudo_bma | 0.346 | 2.5% | 0.011 | 40 |
| holdout_random_walk | stacked | 0.312 | 10.0% | 0.020 | 40 |
| holdout_random_walk | trend | 0.458 | 60.0% | 0.000 | 40 |
| holdout_rotating_quadratic | drift_u | 0.916 | 32.5% | 0.038 | 40 |
| holdout_rotating_quadratic | pseudo_bma | 0.916 | 32.5% | 0.038 | 40 |
| holdout_rotating_quadratic | stacked | 0.916 | 32.5% | 0.039 | 40 |
| holdout_rotating_quadratic | trend | 1.000 | 0.0% | 0.000 | 40 |
| suite_drift | drift_u | 0.000 | 0.0% | 0.018 | 40 |
| suite_drift | lgcp | 0.441 | 82.5% | 0.019 | 40 |
| suite_drift | pseudo_bma | 0.000 | 0.0% | 0.018 | 40 |
| suite_drift | stacked | 0.062 | 35.0% | 0.045 | 40 |
| suite_drift | trend | 0.966 | 12.5% | 0.000 | 40 |
| suite_emergence | drift_u | 0.340 | 57.5% | 0.061 | 40 |
| suite_emergence | lgcp | 0.180 | 50.0% | 0.020 | 40 |
| suite_emergence | pseudo_bma | 0.157 | 25.0% | 0.006 | 40 |
| suite_emergence | stacked | 0.095 | 57.5% | 0.095 | 40 |
| suite_emergence | trend | 0.354 | 100.0% | 0.000 | 40 |
| suite_lane_shift | drift_u | 0.000 | 0.0% | 0.057 | 40 |
| suite_lane_shift | lgcp | 0.000 | 0.0% | 0.019 | 40 |
| suite_lane_shift | pseudo_bma | 0.398 | 87.5% | 0.000 | 40 |
| suite_lane_shift | stacked | 0.224 | 77.5% | 0.031 | 40 |
| suite_lane_shift | trend | 0.398 | 87.5% | 0.000 | 40 |
| suite_stationary | drift_u | 0.000 | 0.0% | 0.036 | 40 |
| suite_stationary | lgcp | 0.000 | 0.0% | 0.020 | 40 |
| suite_stationary | pseudo_bma | 0.000 | 0.0% | 0.002 | 40 |
| suite_stationary | stacked | 0.000 | 0.0% | 0.005 | 40 |
| suite_stationary | trend | 0.073 | 27.5% | 0.000 | 40 |

These are empirical ranks and coverage of latent expected missed mass on the planning grid, not the PIT of realised Poisson counts.
Only expected-objective plans are shown. The complete sweep diagnostics are in `results/calibration_diagnostics.csv`.
No nominal coverage claim or sampler adoption follows from this table alone.
The component sampler and component forecasters reuse fixed Monte Carlo streams across history seeds. These are conditional diagnostics with common random numbers, not 40 independent sampler-noise realizations. History and scenario seeds still vary.
