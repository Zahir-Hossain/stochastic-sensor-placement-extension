| Origin | Method | Policy | Detection | Paired change, pp | Backtests | Weights |
|---:|---|---|---:|---:|---:|---|
| 4 | stacked | original | 78.96% | -2.34 | 1 | pooled=0.0000, recent=0.8368, drift_u=0.1632, trend=0.0000 |
| 4 | stacked | minimum_origins | 81.31% | +0.00 | 1 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 4 | stacked | relative_floor | 78.96% | -2.34 | 1 | pooled=0.0000, recent=0.8368, drift_u=0.1632, trend=0.0000 |
| 4 | stacked | both | 81.31% | +0.00 | 1 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 4 | pseudo_bma | original | 79.08% | -2.23 | 1 | pooled=0.0774, recent=0.9123, drift_u=0.0101, trend=0.0001 |
| 4 | pseudo_bma | minimum_origins | 81.31% | +0.00 | 1 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 4 | pseudo_bma | relative_floor | 79.08% | -2.23 | 1 | pooled=0.0775, recent=0.9123, drift_u=0.0101, trend=0.0001 |
| 4 | pseudo_bma | both | 81.31% | +0.00 | 1 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 5 | stacked | original | 78.45% | -0.78 | 2 | pooled=0.2759, recent=0.6346, drift_u=0.0895, trend=0.0000 |
| 5 | stacked | minimum_origins | 79.23% | +0.00 | 2 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 5 | stacked | relative_floor | 78.45% | -0.78 | 2 | pooled=0.2759, recent=0.6346, drift_u=0.0895, trend=0.0000 |
| 5 | stacked | both | 79.23% | +0.00 | 2 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 5 | pseudo_bma | original | 79.22% | -0.01 | 2 | pooled=0.9947, recent=0.0052, drift_u=0.0001, trend=0.0000 |
| 5 | pseudo_bma | minimum_origins | 79.23% | +0.00 | 2 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 5 | pseudo_bma | relative_floor | 79.22% | -0.01 | 2 | pooled=0.9944, recent=0.0055, drift_u=0.0001, trend=0.0000 |
| 5 | pseudo_bma | both | 79.23% | +0.00 | 2 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 6 | stacked | original | 78.36% | +8.77 | 3 | pooled=0.4380, recent=0.5106, drift_u=0.0513, trend=0.0000 |
| 6 | stacked | minimum_origins | 78.36% | +8.77 | 3 | pooled=0.4380, recent=0.5106, drift_u=0.0513, trend=0.0000 |
| 6 | stacked | relative_floor | 78.36% | +8.77 | 3 | pooled=0.4373, recent=0.5115, drift_u=0.0512, trend=0.0000 |
| 6 | stacked | both | 78.36% | +8.77 | 3 | pooled=0.4373, recent=0.5115, drift_u=0.0512, trend=0.0000 |
| 6 | pseudo_bma | original | 69.59% | +0.00 | 3 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 6 | pseudo_bma | minimum_origins | 69.59% | +0.00 | 3 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 6 | pseudo_bma | relative_floor | 69.59% | +0.00 | 3 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 6 | pseudo_bma | both | 69.59% | +0.00 | 3 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 7 | stacked | original | 74.87% | -1.40 | 3 | pooled=0.9817, recent=0.0000, drift_u=0.0000, trend=0.0183 |
| 7 | stacked | minimum_origins | 74.87% | -1.40 | 3 | pooled=0.9817, recent=0.0000, drift_u=0.0000, trend=0.0183 |
| 7 | stacked | relative_floor | 74.87% | -1.41 | 3 | pooled=0.9816, recent=0.0000, drift_u=0.0000, trend=0.0184 |
| 7 | stacked | both | 74.87% | -1.41 | 3 | pooled=0.9816, recent=0.0000, drift_u=0.0000, trend=0.0184 |
| 7 | pseudo_bma | original | 76.27% | -0.00 | 3 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 7 | pseudo_bma | minimum_origins | 76.27% | -0.00 | 3 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 7 | pseudo_bma | relative_floor | 76.27% | -0.00 | 3 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |
| 7 | pseudo_bma | both | 76.27% | -0.00 | 3 | pooled=1.0000, recent=0.0000, drift_u=0.0000, trend=0.0000 |

Paired changes use the same default historical KDE reference. Minimum-origin fallback uses pooled history before three usable backtests. Relative floors are an experimental score ablation; defaults are unchanged. Full-precision weights and solver status are retained in the raw CSV.
