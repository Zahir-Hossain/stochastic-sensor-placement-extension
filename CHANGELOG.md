# Changelog

## 2.1.0 (2026-11-02)

### Added

- Chronological line-intensity forecast comparisons, explicit stress tests,
  sampler diagnostics and a small-grid transport ambiguity study.
- Independent checks for gradients, CVaR, TV and transport objectives,
  including study-scale primal/dual comparisons and concentrated masses.
- Raw results, provenance checks, reproducible tables, a technical report,
  a tutorial and a VS Code setup workflow.
- An animated README overview and a social preview card, rendered from the
  saved plans and scores by `scripts/make_animation.py`.

### Corrected

- Prefix-only bandwidth fitting, AIS epoch alignment and trajectory splitting,
  convex intensity stacking, solver-fallback reporting and fractional CVaR.
- Drift and bandwidth handling at the line-space seam, leave-one-out kernel
  scoring, nonlinear-risk warnings and the scope of conditional certificates.
- AIS bandwidth claims and component comparisons; disclose calibration
  fallback, grid-edge selections, discrete plans and common sampler draws.

### Documentation

- Lead with where forecasts help and fail, using an overview generated from
  saved runs. Report the negative reversal, AIS, sampler and ambiguity outcomes.
- Distinguish locally frozen designs from externally timestamped registration.
- Separate current findings and validation from archived review logs.
- Remove claims that unpublished tags already exist.

No candidate sampler or experimental AIS policy replaces a default. The
multi-week AIS study remains blocked by archive access. Version 2.1 is a
working report version; no tag or GitHub release is claimed.

## 2.0.0 (November 2026)

Rebuilt the original MATLAB demonstration as the Python `stochplace` package
with future-traffic evaluation, independent numerical checks and a complete
reproduction workflow.

## Original MATLAB version (June 2026)

Preserved in `legacy/` and published commit `b67f3a5`.

The [detailed development record](docs/history/CHANGELOG_detail.md) retains
all earlier audit items, historical check counts and correction decisions.
Current evidence is indexed in [validation](docs/validation.md).
