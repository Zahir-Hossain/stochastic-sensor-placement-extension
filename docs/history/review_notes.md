# Research validity review: revision 2.1

The revision was reviewed against the implementation, experiment design and
the original barrier-coverage paper. These are substantive corrections,
not evidence of a new state-of-the-art method.

| Issue in revision 2.0 | Correction | Verification |
|---|---|---|
| The ensemble backtests reused a bandwidth chosen from later observations. | Fit bandwidth independently on every rolling training prefix. | Regression test records exactly which prefixes the selector sees. |
| Softmax of individual forecast scores was called stacking. | Preserve it as `pseudo_bma`; implement convex Poisson intensity stacking separately. | Complementary-model example requires mixed weights while pseudo-BMA selects a single model. |
| CVaR rounded the tail up to a whole number of samples. | Include the fractional quantile observation in the value and subgradient. | Independent epigraph LP, including 32 samples at beta 0.9. |
| Raw canonical angles could jump across the representation seam. | Lift headings continuously, flip signed offsets consistently, and use seam-aware bandwidth scales. | Recover drift velocity across the seam; compare equivalent bandwidth representations. |
| A leave-one-out kernel retained images of its own point. | Remove the observation and both of its images. | Kernel and boundary tests. |
| A fitted AIS piece could span a train/test epoch boundary. | Split reports by epoch before fitting any line; also split at exits and low-speed reports. | Boundary-crossing fixture produces two pieces with disjoint epochs. |
| The expected-void objective was described as penalising bad futures more. | Explain its soft-min behaviour and distinguish it from tail risk. | Jensen ordering and objective-gradient checks. |
| The predictive-mean identity was used to assert a necessary posterior-weight condition. | State the identity and its sufficient Bayesian interpretation without an iff claim. | Corrected derivation in `theory.md`. |
| The oracle and the regret bound could be interpreted too strongly. | Call the oracle a true-intensity heuristic reference; retain the measured optimisation comparison term. | Small exact subset comparisons and explicit limitations. |
| Results depended on software versions without a complete source fingerprint. | Record source SHA-256, dependency versions, config and Git revision; include a Python 3.12 snapshot. | Reproduction pipeline and artifact checks. |

The TV-ball experiment changes the optimisation objective itself. Its inner
adversarial problem is checked against a separate linear program. Its outer
sensor search is a finite-grid heuristic, and its conditional certificate
is scoped explicitly to the grid and ambiguity set. Choosing a radius does
not establish that real future traffic lies within that radius.

All revision 2.0 output tables and figures are regenerated for this release.
Old numerical claims should not be carried forward without recomputation.
