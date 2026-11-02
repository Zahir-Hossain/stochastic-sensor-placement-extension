# Forecast-aware placement with corrected validation and explicit robustness

The earlier rebuild reused future-informed bandwidths inside historical
backtests, described pseudo-BMA as stacking and rounded CVaR tails to whole
samples. This revision corrects those behaviours, splits AIS observations
at epoch boundaries before fitting lines, and adds seam-aware drift handling.

The project now separates intensity stacking and pseudo-BMA, includes a
finite-grid TV ambiguity objective with an exact inner adversary, and
reports reversal stress tests alongside successful forecasting cases.
All studies, figures and the report are regenerated. VS Code tasks, an
isolated setup, pinned reference dependencies and an artifact verifier
make the repository runnable and reviewable.

Validation: 118 local tests passed; the Octave parity test was skipped
because Octave is unavailable locally. Ruff, formatting and Mypy pass.
All nine result sets match the source fingerprint and their recomputed
checks. The executed tutorial and compiled report are included.

The CI workflow still needs to run on GitHub. The one-day AIS study is a
demonstration, and the TV certificate is conditional on its finite-grid
ambiguity set; neither supports an operational deployment claim.
