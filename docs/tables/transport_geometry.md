| Regime | Ball | Future gain over nominal, pp [95% paired CI] | Truth inside ball | Changed plans | Mean worst-case gain, pp |
|---|---|---:|---:|---:|---:|
| drift | tv | -0.476 [-0.858, -0.095] | 100% | 5/20 | +0.045 |
| drift | w1 | -10.378 [-12.405, -7.865] | 100% | 20/20 | +6.548 |
| emergence | tv | +0.000 [+0.000, +0.000] (D) | 65% | 0/20 | +0.000 |
| emergence | w1 | -5.274 [-5.738, -4.757] | 50% | 20/20 | +3.763 |
| lane_shift | tv | -1.085 [-1.640, -0.586] | 100% | 10/20 | +0.134 |
| lane_shift | w1 | -18.263 [-20.759, -16.684] | 100% | 20/20 | +10.293 |
| reversal | tv | -0.519 [-1.618, +0.428] | 20% | 3/20 | +0.041 |
| reversal | w1 | -16.070 [-16.070, -16.070] (D) | 30% | 20/20 | +10.735 |
| seam_drift | tv | -2.816 [-3.840, -1.792] | 100% | 11/20 | +0.129 |
| seam_drift | w1 | -2.114 [-3.423, -1.052] | 100% | 8/20 | +0.121 |
| stationary | tv | +0.000 [+0.000, +0.000] (D) | 100% | 0/20 | +0.000 |
| stationary | w1 | -0.835 [-0.982, -0.688] | 95% | 17/20 | +0.786 |

All six regimes and 20 seeds are included. The certificate applies only to normalized truth on the planning grid when it lies in the ball. Three training calibration errors do not establish nominal coverage. TV and W1 radii have different units. The discrete outer search is a heuristic; this is an exploratory small-grid study.

The first calibration target (5) uses four history epochs: stacking has no usable weight-validation backtest and returns pooled history. Thus radii can be driven by an immature pooled forecast rather than the eight-epoch stacked plan. This also affects the first residual-bootstrap factor in C3. These negative results are conditional on the fixed calibration rule; they do not isolate geometry as the cause. The rule and all original outcomes are retained.

| Regime | Ball | Distinct nominal plans | Distinct robust plans |
|---|---|---:|---:|
| drift | tv | 2 | 2 |
| drift | w1 | 2 | 2 |
| emergence | tv | 2 | 2 |
| emergence | w1 | 2 | 7 |
| lane_shift | tv | 3 | 2 |
| lane_shift | w1 | 3 | 4 |
| reversal | tv | 1 | 3 |
| reversal | w1 | 1 | 1 |
| seam_drift | tv | 1 | 2 |
| seam_drift | w1 | 1 | 3 |
| stationary | tv | 2 | 2 |
| stationary | w1 | 2 | 2 |

Intervals marked (D) have zero width and are degenerate; they reflect repeated discrete plans, not high population precision.

| Regime | Ball | First error attains radius | Median radius / realized truth distance |
|---|---|---:|---:|
| drift | tv | 20/20 | 5.02 |
| drift | w1 | 20/20 | 6.44 |
| emergence | tv | 1/20 | 1.14 |
| emergence | w1 | 1/20 | 1.05 |
| lane_shift | tv | 20/20 | 3.98 |
| lane_shift | w1 | 20/20 | 13.16 |
| reversal | tv | 20/20 | 0.98 |
| reversal | w1 | 20/20 | 0.97 |
| seam_drift | tv | 20/20 | 9.10 |
| seam_drift | w1 | 20/20 | 4.22 |
| stationary | tv | 6/20 | 1.85 |
| stationary | w1 | 4/20 | 3.01 |

The ratio is a retrospective diagnostic; truth distances are never used to choose radii.
