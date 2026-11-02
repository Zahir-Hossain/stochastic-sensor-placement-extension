# Part A audit corrections and validation

> Archived validation as of `c9e6688`. Statements below describe that checkpoint,
> not the current Part B/C branch. Later validation is recorded separately.

Part A is complete on `research-hardening`. Part B and Part C have not
started. Nothing was pushed, tagged, rebased or rewritten. This is a local
review checkout; the user's existing Mac checkout has not been changed.

## Item commits

```text
3ce5804 A1 [disclosure] Report expected-void drift failure and paired uncertainty
63e14c7 A2 [disclosure] Reproduce post hoc AIS bandwidth sensitivity
94a9d14 A3 [disclosure] Qualify headline gains by scenario and model match
6635b3d A4 [disclosure] Report TV ambiguity as a negative result
977aeb4 A5 [disclosure] Remove assignment framing from prototype references
8f7bb2c A6 [confirmed defect] Align pandas pins and verifier dependencies
003695f A7 [disclosure] Label predictive risk comparisons as uncalibrated
00461ff A8 [confirmed defect] Report AIS origins and paired baseline differences
```

The closing validation commit follows these item commits. Each item is
classified in its commit and in `CHANGELOG.md`.

## Changes and numerical provenance

| Item | Result | Committed generator and source |
|---|---|---|
| A1, disclosure | Lower mean detection than history under drift, with a paired interval including zero; retain the negative result | `scripts/void_failure_analysis.py`, reading `results/suite_drift/runs.csv`; outputs `docs/tables/void_failure.md` and `paper/void_numbers.tex` |
| A2, disclosure | Post hoc bandwidth sensitivity only; no new scale is adopted | `scripts/ais_bandwidth_sensitivity.py`; raw origin-level runs, summary and provenance in `results/ais_bandwidth_sensitivity/`; default scale matches the published AIS study |
| A3, disclosure | Headline successes closely match candidate-model assumptions; reversal remains a loss | `scripts/research_summary.py`, `results/robustness/summary.csv`, `paper/robust_numbers.tex` |
| A4, disclosure | TV ambiguity is a negative result, with near-constant penalties and limited truth coverage | `scripts/research_summary.py`, reading `results/robustness/runs.csv`; outputs `docs/tables/tv_scope.md` and report macros |
| A5, disclosure | Remove assignment framing from the prototype references | README and START_HERE wording only |
| A6, confirmed defect | Verifier compatibility, explicit packaging dependency and aligned pandas runtime/stubs | `scripts/verify_artifacts.py`, `pyproject.toml`, `requirements/reproduce-py312.txt` |
| A7, disclosure | Void/CVaR samples are uncalibrated sensitivity inputs; both learned combiners use component sampling, fixed mixture has no samples | README objectives, theory and report; package implementation unchanged |
| A8, confirmed reporting defect | Show every AIS origin and paired historical-KDE differences rather than bootstrap intervals in tables | `scripts/ais_origin_table.py`, called by both table generators, reading `results/ais_gothenburg/runs.csv` |

The AIS figure is preserved and its caption identifies its old error bars
as descriptive resampling summaries. The new per-origin table is the
preferred evidence. Every original method, including expected-void, is
retained. The external Claude audit PDF is an unchanged review snapshot;
its stale wording is not adopted as the repository's interpretation.

The derived `results/key_numbers.json` changes only in final floating-point
digits after the pandas upgrade. Its generating script and raw sources
remain documented; original study summaries are untouched.

## Integrity

All 28 original raw/summary/provenance files are byte-identical to `v2.1.0`.

`src/`, `configs/` and `legacy/` are unchanged. The required command
`git diff --stat v2.1.0 -- src/` produces empty output:

```text
```

## Environment and limitations

The isolated Python environment has system-site-packages disabled and is
installed from every exact pin in `requirements/reproduce-py312.txt`.
The reference pandas runtime was raised to match the pinned pandas-stubs.
The verifier also passes with the previous pandas runtime; see both logs.

Registry downloads were not used. Exact-version wheels were reconstructed
from the available local installed distributions, then installed into the
isolated environment with pip's dependency resolver. `pip check` passes.
This establishes local isolation and pinned-version compatibility, not
independent integrity verification of newly downloaded registry wheels.

The first full-check invocation could not launch Ruff because the local
wheel reconstruction lost its executable permission. That failed invocation
is preserved in `validation/part_a/a6_launcher_failure.log`. The installed
binary was hash-checked against the original and its original executable
mode restored. No source, assertion, threshold or tolerance was changed.
The complete checks then passed and were repeated after the table changes.

Octave is unavailable here, so its parity test is skipped. Hosted CI has
not run for these unpublished commits. The original experiments were not
fully rerun during Part A. The additional AIS sensitivity runs and the
small examples are distinct from checking saved-result consistency.

## Full final quality-check output

```text

Running: /workspace/scratch/01a50792c147/.part-a-lock-venv/bin/python -m ruff check src tests scripts examples
All checks passed!

Running: /workspace/scratch/01a50792c147/.part-a-lock-venv/bin/python -m ruff format --check src tests scripts examples
43 files already formatted

Running: /workspace/scratch/01a50792c147/.part-a-lock-venv/bin/python -m mypy
Success: no issues found in 18 source files

Running: /workspace/scratch/01a50792c147/.part-a-lock-venv/bin/python -m pytest --cov=stochplace --cov-report=term-missing
......................................s................................. [ 60%]
...............................................                          [100%]
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.12.14-final-0 _______________

Name                           Stmts   Miss Branch BrPart  Cover   Missing
--------------------------------------------------------------------------
src/stochplace/__init__.py        12      0      0      0   100%
src/stochplace/_typing.py          7      0      0      0   100%
src/stochplace/ais.py            173      7     44      7    94%   72, 135, 141, 179, 193, 280, 294
src/stochplace/cli.py             69     22      6      0    65%   13-25, 29-32, 36-39, 55-61
src/stochplace/evaluate.py        34      1      2      1    94%   65
src/stochplace/experiment.py     220      9     52      8    94%   132, 179, 237, 263, 269-271, 275, 277, 333->335
src/stochplace/figures.py        340    169     60      2    49%   180-282, 286-295, 299-327, 403->401, 419->427, 462-475, 479-490, 555-637, 641-653
src/stochplace/forecast.py       278     13     64     12    93%   78, 80, 84, 87, 89, 97, 107, 109, 153-154, 173, 508, 556
src/stochplace/geometry.py        89      0      8      0   100%
src/stochplace/grid.py           144      5     24      4    95%   43, 175, 177, 209, 222
src/stochplace/intensity.py      202     10     52     10    92%   104-106, 176, 178, 181, 183, 188, 192, 198, 245->261, 253->258
src/stochplace/legacy.py          59      0     10      0   100%
src/stochplace/objective.py      118      4     36      3    95%   103, 150, 202-203
src/stochplace/optimize.py       116      7     34      7    91%   87, 107, 110, 115->131, 126-128, 129->115, 189
src/stochplace/risk.py            59      6     12      6    83%   26, 28, 51, 53, 55, 84
src/stochplace/robustness.py     110     25     18      3    75%   81, 106, 112-113, 157-195
src/stochplace/scenarios.py      100      1     10      1    98%   99
src/stochplace/sensors.py         58      2     10      1    96%   53, 94
--------------------------------------------------------------------------
TOTAL                           2188    281    442     65    85%
118 passed, 1 skipped in 27.09s

Running: /workspace/scratch/01a50792c147/.part-a-lock-venv/bin/python examples/quickstart.py
stacking weights: {'pooled': 0.0, 'recent': 0.0, 'drift_u': 0.834, 'trend': 0.166}
historical detects 92.04% of future trajectories   sensors: [[-5.44, -1.19], [-5.69, 0.03], [-4.5, -2.34], [-6.49, 1.34]]
stacked    detects 95.38% of future trajectories   sensors: [[-0.31, 1.99], [-0.96, 3.0], [0.46, 0.9], [-2.28, 3.95]]

All requested checks passed.
Octave parity is skipped locally because Octave is unavailable; CI has a dedicated parity job.
```

## Full final artifact-verifier output

```text
OK ais_bandwidth_sensitivity: 120 runs; default scale matches published AIS
OK ais_gothenburg: 52 runs
OK approximation: 100 runs
OK data_scarcity: 1200 runs
OK drift_sweep: 5280 runs
OK robustness: 1440 runs
OK suite_drift: 680 runs
OK suite_emergence: 680 runs
OK suite_lane_shift: 680 runs
OK suite_stationary: 680 runs
All 10 result sets match source 71c50eb98ced.
```

## Next stage

Part B changes package source: warnings for uncalibrated component samples
(including pseudo-BMA), a separate mean-field warning for fixed mixture,
one AIS epoch origin, a recorded stacking-fit fallback and TV search from
both greedy and nominal starts. Those changes require one full regeneration
and comparison with the pre-B summaries. Weighted-sum sampling remains a
research proposal; it has not been adopted. New methods and calibration
studies require the separate preregistration stage.
