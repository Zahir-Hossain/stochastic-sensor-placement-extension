# Changelog

- C-close [disclosure]: preserve all preregistered C1-C6 outcomes and negative
  results, reject both sampler candidates under the frozen gate, regenerate
  and verify 19 result sets, record 152 passing tests and the local Octave
  skip, and render the complete report appendix. C7 and external Claude
  review remain explicitly incomplete.

- C-validation [confirmed defect]: retain all tiny probability masses in
  transport calibration, disable a falsely infeasible LP presolve and check
  marginal residuals. Add the observed numerical fixture and rerun C5.
- C-report [confirmed defect]: render the original report's figures against
  its fixed original studies so newly added folders cannot silently change
  the sensitivity figure's population while an experiment is writing.

- C-validation [confirmed defect]: keep specialized runner configurations in
  `configs/research/` so the general experiment CLI receives only its own
  schema; make repository research helpers importable under the pytest CLI.
  Protocol values and package source are unchanged.

## Proposed research stage (November 2026)

- C-plan [proposed method change]: preregister new scenarios, latent-sample
  diagnostics, sampler gates, AIS controls, transport ambiguity and the
  externally blocked multi-week holdout before running new outcomes.

- C1 [proposed method change]: add five preregistered nonlinear, random
  and splitting lane regimes, with independent scenario seeds and new
  frozen configs. No original scenario or config is changed.

- C2 [proposed method change]: record empirical ranks and equal-tail
  coverage for latent expected misses on the planning grid, plus sample-
  mean mismatch. These are not a realised-count PIT or field validation.

- C3 [proposed method change]: freeze weighted-resampling and chronological
  residual sampler candidates with a fixed eligibility gate on all new
  regimes. Neither replaces the current sampler or establishes calibration.

- C4 [proposed method change]: freeze a common-KDE AIS reanalysis that
  chooses bandwidth by training-only chronological placement loss at every
  origin. It remains exploratory because the one-day sample was seen.

- C6 [proposed method change]: freeze minimum-origin and relative-floor
  AIS ablations, record per-origin weights, and independently check the
  modified convex objective's gradient. Original policies stay defaults.

- C5 [proposed method change]: freeze a small-grid line-geometry transport
  experiment with training-only empirical radii. Verify the numerical dual
  against an independent primal LP; make no calibrated-coverage claim.

- C7 [disclosure]: record the preregistered multi-week AIS specification
  and actual archive-access failure. No raw data, checksum or result is
  fabricated; this external-data study remains blocked.

## Part B corrections (November 2026)

- B-close [disclosure]: regenerate all studies, verify that only corrected
  TV rows change, record full validation and archive the Part A checkpoint.

- B1 [confirmed defect]: warn on uncalibrated component-sampled void/CVaR
  inputs for stacking and pseudo-BMA; distinguish the sample-free fixed
  mixture. Keep all strategies runnable and all negative results intact.

- B2 [confirmed defect]: anchor AIS extraction, study grouping and the
  verifier at the earliest report's calendar midnight; cover the latent
  five-hour boundary mismatch with a fixture.

- B3 [confirmed defect]: fall back to held-out-score pseudo-BMA weights
  when SLSQP fails, preserve its message and record fit status per run.

- B4 [confirmed defect]: refine TV plans from both TV greedy and nominal
  stacked starts, evaluate each start on the TV objective and record which
  wins. Robustness numbers are expected to change after regeneration.

## Part A corrections (November 2026)

- A1 [disclosure]: expose the saved expected-void drift failure, paired
  uncertainty and component-weight association with a reproducible script.

- A2 [disclosure]: commit a reproducible post hoc AIS bandwidth probe,
  verify its default-scale agreement and qualify the estimator comparison.

- A3 [disclosure]: state the scenario-to-model match beside the headline
  results and retain the reversal loss as an experimental-design limit.

- A4 [disclosure]: present unstructured TV ambiguity as a negative result,
  remove robust-design framing from the package description and report,
  and generate penalty and truth-coverage statements from saved runs.

- A5 [disclosure]: call the preserved prototype the original MATLAB
  version, removing assignment framing from the entry-point documents.

- A6 [confirmed defect]: apply the verifier's pandas compatibility fix,
  declare its direct packaging dependency, and raise the reference runtime
  pin to pandas 3.1.0 to match pandas-stubs 3.1.0.261029. Saved result
  provenance retains its original pandas version; no results are rerun.

- A7 [disclosure]: label sample-based void and CVaR results as uncalibrated
  sensitivity analyses, distinguish both component samplers from the
  sample-free fixed mixture, and retain weighted-sum sampling as a proposal.

- A8 [confirmed defect]: replace AIS table bootstrap intervals with each
  test origin's detection and paired difference from historical KDE, using
  shared generators. Preserve all methods and the descriptive old figure.

- A-close [disclosure]: record all Part A validation and limitations,
  preserve the initial local launcher failure, verify frozen inputs and
  results, and rebuild the report with checked layout.

## 2.1.0 (November 2026)

### Corrected
- Refit bandwidth inside each rolling-origin training prefix.
- Distinguish pseudo-BMA from convex Poisson intensity stacking.
- Include fractional quantile mass in CVaR values and subgradients.
- Handle drifting lanes and bandwidth scales across the line-space seam.
- Exclude a left-out observation and all its images in kernel CV.
- Split AIS reports at epoch boundaries before fitting line segments.
- Correct objective interpretations and the scope of mathematical claims.

### Added
- Exact finite-grid TV adversary with independent LP verification, a
  conditional detection certificate and an exchange-search outer heuristic.
- Drift-reversal and seam-crossing stress scenarios, with negative results.
- VS Code workspace, tasks, debug configurations, isolated setup, a tested
  Python 3.12 dependency snapshot and a single reproduction entry point.
- Raw regenerated results, source fingerprints, artifact verification,
  revised report, executed tutorial and project walkthrough.

The original MATLAB script and `v0.1.0` tag are preserved.

## 2.0.0 (November 2026)

Complete rebuild as a tested Python package with a research-grade
evaluation. See `legacy/README.md` for what changed relative to v0.1 and why.

### Added
- `stochplace` package: representation-space geometry, cell-integrated
  kernel and LGCP (Laplace) intensity estimation, Moebius seam handling,
  sensor models, void-probability objectives (expected, expected void
  probability, CVaR), greedy selection with gradient refinement.
- Forecasters for future trajectory intensity (pooled, recent, drift,
  drift with predictive uncertainty, log-linear trend) and stacking by
  held-out log score (`lambda_E` with learned weights).
- Synthetic scenarios with known future truth (stationary, drifting lane,
  lane shift, lane emergence) and a config-driven Monte Carlo runner.
- AIS case study on public Danish Maritime Authority data (Gothenburg).
- Misspecification regret bound with proofs (`docs/theory.md`) and an
  empirical check on every run.
- Python port of the v0.1 MATLAB script, verified against the unchanged
  script in GNU Octave.
- CI (lint, types, tests on Python 3.10 to 3.13, Octave parity, smoke runs),
  citation metadata, technical report.

### Changed
- The original MATLAB script moved to `legacy/matlab/` (content unchanged).

## 0.1.0 (June 2026)

- Original MATLAB toy simulation: synthetic routes, Gaussian-smoothed maps,
  greedy placement for historical, shifted and perturbed route sets.
