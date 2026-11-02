| Origin | Method | Training-selected scale | Detection | Change from default historical KDE, pp |
|---:|---|---:|---:|---:|
| 4 | pooled | 0.25 | 87.35% | +6.04 |
| 4 | recent | 0.25 | 88.22% | +6.91 |
| 4 | stacked | 0.25 | 87.53% | +6.23 |
| 5 | pooled | 0.25 | 84.53% | +5.30 |
| 5 | recent | 0.25 | 83.65% | +4.42 |
| 5 | stacked | 0.25 | 84.36% | +5.13 |
| 6 | pooled | 0.25 | 75.02% | +5.44 |
| 6 | recent | 0.25 | 80.54% | +10.95 |
| 6 | stacked | 0.25 | 81.07% | +11.48 |
| 7 | pooled | 0.25 | 92.24% | +15.96 |
| 7 | recent | 0.25 | 78.80% | +2.53 |
| 7 | stacked | 0.25 | 77.23% | +0.96 |

Every origin is shown. Scale selection uses training targets only. This reuses the already viewed one-day sample and is exploratory; overlapping origins are not independent population replicates.

12/12 choices select 0.25, the lower edge of the frozen grid; the grid does not bracket an interior optimum. It is not extended on this reused day. Stacking exceeds pooled history at 2/4 origins; its largest deficit, at origin 7, drives the mean comparison.

| Origin | Training-selected stacking minus training-selected pooled, pp |
|---:|---:|
| 4 | +0.19 |
| 5 | -0.17 |
| 6 | +6.04 |
| 7 | -15.01 |
