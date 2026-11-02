# Current validation

The current record is [audit_followup.md](audit_followup.md). It separates
local checks, the external Claude audit, and hosted CI on an explicit commit.
Initial Part A/B/C records are historical checkpoints.

## Archived revision 2.1 validation

The following record predates the corrections and research extension; its
118-test and nine-result counts are historical, not current.


The reference run used Linux and Python 3.12.14. An isolated environment was
installed from `requirements/reproduce-py312.txt`, then the project was
installed in editable mode with its development and lint extras.

| Check | Completed result |
|---|---|
| Ruff lint | Pass for `src`, `tests`, `scripts` and `examples` |
| Ruff formatting | Pass |
| Mypy | Pass for 18 package source files |
| Full pytest suite | **118 passed, 1 skipped** |
| Reported coverage, including branches | **85%** |
| Octave parity | Skipped locally: GNU Octave is unavailable |
| Quickstart | Executed successfully in the isolated environment |
| Robust-placement example | Executed; prints certificate scope and future TV distance |
| Learning notebook | All 9 code cells executed, 2 rendered figures, no error outputs |
| Small reproduction pipeline | Two seeds per setting; all generated result sets verified |
| Full synthetic studies | All configured 40-seed studies regenerated |
| Robustness study | Six scenarios, 20 seeds, three radii, four strategies |
| AIS demonstration | Raw 14.3 MB download checksummed; 84,702 reports, 265 retained pieces |
| Greedy approximation study | 100 instances, exact finite-subset comparison |
| Result provenance | All 9 result sets match the runtime source fingerprint |
| Raw-run consistency | Unique keys, recomputed synthetic summaries and in-scope certificates verified |
| Technical report | Compiled from regenerated tables and figures; visually reviewed |
| Hosted GitHub CI | Configured; requires pushing the branch to run |

The machine-readable local check record is [validation.json](validation.json).
It records the commands, execution times, environment and overall result.
The notebook was executed through IPython in-process because this execution
environment restricts local kernel sockets; the standard notebook kernel
mode remains available for local authoring.

## Interpret the checks correctly

The 118 passing tests include the longer statistical tests. The one skipped
test compares the original MATLAB script with its Python port through
Octave. The GitHub workflow installs Octave for a dedicated parity job.
Only Python 3.12 was executed locally; the workflow defines additional
Python 3.10, 3.11 and 3.13 jobs.

The artifact verifier preserves binary64 values with round-trip CSV parsing.
Default CSV parsing can change the sign of machine-precision ties and thus
change strict win counts, even when means are numerically identical.

A source fingerprint is independent of documentation-only Git commits.
The result metadata records the repository state observed during each
study, including a dirty suffix where authoring files were being edited.
The package-source fingerprint is checked exactly against this release.
Cross-platform bitwise reproducibility is not claimed.

Green software checks do not establish calibrated forecast uncertainty,
operational sensor performance, universal superiority or a publication-level
novelty claim. The report and research boundary state the relevant scope.

## Repeat the checks

```bash
python scripts/check.py --full
python scripts/verify_artifacts.py
python examples/robust_placement.py
```

To regenerate the notebook:

```bash
python -m pip install -e ".[notebook]"
python scripts/build_tutorial.py
```

Use `--in-process` for environments without local kernel sockets.
