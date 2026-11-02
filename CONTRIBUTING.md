# Contributing

Use Python 3.12 for the reference workflow:

```bash
python3.12 scripts/bootstrap.py
source .venv/bin/activate
python scripts/check.py --full
```

Keep numerical tests independent of the implementation where possible:
finite differences for derivatives, separate LPs for risk measures, and
exhaustive enumeration for small candidate sets. Include a chronological
validation fixture when modifying forecasting or preprocessing.

For a method change, rerun the relevant studies and update the report.
`python scripts/reproduce.py --workers 2` writes a complete reproduction to
`output/reproduction/`. Add `--in-place` deliberately to refresh tracked
results. `python scripts/verify_artifacts.py` checks their provenance.

Every mathematical claim must state its assumptions and guarantee scope.
Keep inherited methods attributed and retain unsuccessful cases. The
research boundary is in `docs/research_boundary.md`.

Do not commit raw AIS downloads, virtual environments, credentials or
machine-specific settings. The unchanged legacy MATLAB script is retained
for historical comparison; extend the Python package for new work.
