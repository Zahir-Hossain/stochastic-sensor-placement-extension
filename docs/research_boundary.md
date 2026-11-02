# Research boundary and attribution

## Inherited framework

Kim, Stilwell, Yetkin and Jimenez, *Near-optimal Sensor Placement for
Detecting Stochastic Target Trajectories in Barrier Coverage Systems*
(arXiv:2505.00825, 2025), supplies the barrier-coverage setting, line-space
representation, LGCLP modelling approach, void-probability formulation and
greedy placement with numerical refinement. Its real-data study concerns
Hampton Roads, Virginia. The earlier IEEE Access paper (2023) treats
uncertain intensities and the void-probability/Jensen perspective.

The line representation is standard geometry; greedy submodular
approximation, stacking, CVaR, Gaussian convolution and robust observation
selection also have established literatures. Their use here does not make
them new mathematical inventions.

## This repository's extension

1. An independently implemented Python pipeline that forecasts future line
   intensities and evaluates sensor placement against future traffic.
2. Strictly chronological intensity stacking, compared with pseudo-BMA,
   recent observations, drift, a fixed mixture and pooled-history methods.
3. Side-by-side expected, predictive-void and fractional-tail CVaR
   objectives, with their distinct interpretations stated explicitly.
4. Stress tests including an unannounced drift reversal and a lane crossing
   the representation seam, plus an AIS demonstration at a different site.
5. Reproducible configurations, source fingerprints, raw outputs,
   independent numerical checks, a learning notebook and a VS Code workflow.

These constitute a research software extension and comparative study.
A publication-level novelty claim requires a broader literature review and
stronger empirical evidence than this repository presently establishes.

## Reported negative result: TV ambiguity

The equal-total TV experiment has an exact finite-grid inner adversary,
but its penalty changes little across saved plans and its uncalibrated
radius excludes several shifted truths. It is reported as a limitation of
this ambiguity construction, rather than a demonstrated design advance.
The code, tables, figures and conditional certificate remain available.
See the [generated penalty and coverage analysis](tables/tv_scope.md).

## Important boundaries

* The LGCP is a lattice Laplace/empirical-Bayes implementation with plug-in
  hyperparameters. It is not INLA and does not reproduce the base paper's
  results. KDE is an additional baseline, not the base paper's estimator.
* Synthetic traffic is designed to expose assumptions. Constant-velocity
  drift matches the drift forecaster, logit-linear lane shares resemble
  the log-linear trend model, and stationary traffic matches pooled
  history. Success in these regimes tests selection of a well-specified
  candidate, not generalisation to arbitrary shifts. The reversal is
  outside all candidate families and is a loss for stacking. This is a
  high-severity experimental-design limitation for interpreting the
  headline gains. Traffic is not sampled from a representative population.
* The oracle is the same heuristic given true future intensity; it is not
  a certified global optimum or strict upper bound on every reported run.
* The intensity-error inequality is an elementary sensitivity diagnostic.
  Its empirical verification is not independent evidence of novelty.
* The exact TV inner solution does not make outer sensor placement exact.
  Its certificate is conditional on the chosen grid and ambiguity set.
* Sensors are distance-based and conditionally independent. Propagation,
  bathymetry, deployment costs, correlated detection and curved trajectories
  are outside the model.
* The AIS study is one day at one location with four rolling origins.
  Its scores are modelled probabilities per straight piece, not observed
  physical sensor performance or operational validation.

The unchanged MATLAB prototype and its original figures remain in
`legacy/`; `v0.1.0` marks the original Git version.

## Transport and coverage attribution

Wasserstein distributionally robust optimization and its dual reformulation
are established: [Gao and Kleywegt](https://doi.org/10.1287/moor.2022.1275)
and [Mohajerin Esfahani and Kuhn](https://doi.org/10.1007/s10107-017-1172-1).
Related [distributionally robust coverage control](https://doi.org/10.1109/CDC49753.2023.10384225)
also predates this study. The exploratory line-space comparison is not a
new general DRO theorem or an exhaustive comparison with this literature.
Its negative result is conditional on the fixed calibration prefixes,
including a first prefix that returns pooled history.
