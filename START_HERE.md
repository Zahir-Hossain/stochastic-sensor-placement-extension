# Open and run the project

This folder is the complete Git repository. It includes source, tests,
experiment configurations, generated results, figures and the technical report.
The original MATLAB version remains in `legacy/` and at published commit `b67f3a5`.

## VS Code on macOS

1. Extract the archive into a fresh folder.
2. Open `stochplace.code-workspace` in VS Code.
3. Install the recommended Python and Ruff extensions if prompted.
4. Open **Terminal > New Terminal** and run:

   ```bash
   python3.12 scripts/bootstrap.py
   ```

   Python 3.10-3.13 is supported. Python 3.12 is the reference environment.
   If your Python 3.12 command is `python3`, use that command instead.
5. Press **Cmd+Shift+P**, choose **Python: Select Interpreter**, and select
   `.venv/bin/python`. Open a new terminal after selecting it.
6. Run:

   ```bash
   python scripts/check.py
   python examples/quickstart.py
   python examples/robust_placement.py
   ```

Alternatively use **Terminal > Run Task**. Tasks 1-5 cover setup, verification,
the quickstart, a small robustness experiment and full research reproduction.
The Run and Debug panel includes the quickstart and a small experiment.

No Docker, database, account credentials or GPU is required.

## What to read

| Goal | File |
|---|---|
| Understand the question and findings | `README.md` |
| Read the technical report | `paper/main.pdf` |
| Check the derivations | `docs/theory.md` |
| Distinguish inherited methods from this extension | `docs/research_boundary.md` |
| See what was corrected | `CHANGELOG.md` |
| Prepare to explain the work | `docs/project_walkthrough.md` |
| Inspect recorded checks and reproduction | `docs/validation.md` |
| Read the learning notebook | `examples/tutorial.ipynb` |

## Reproduce results

First run a small complete pipeline:

```bash
python scripts/reproduce.py --seeds 2 --workers 2 --skip-ais
```

It writes to `output/reproduction/`, leaving the committed results alone.
For all configured seeds and the raw AIS study:

```bash
python scripts/reproduce.py --workers 2
```

Add `--paper` if a LaTeX distribution with `latexmk` is installed.
Use `python scripts/bootstrap.py --locked` on Python 3.12 for the tested
dependency snapshot. Octave is optional locally; it is needed only for
the original MATLAB parity test.

## Git and GitHub

The current Python work is published on `research-hardening` in
[PR #1](https://github.com/Zahir-Hossain/stochastic-sensor-placement-extension/pull/1).
The default `main` branch still contains the original MATLAB version until
that PR is merged. The review branch has eight CI jobs, including a Python
3.10-3.13 matrix and GNU Octave parity.

To inspect the published work from a fresh clone:

```bash
git clone https://github.com/Zahir-Hossain/stochastic-sensor-placement-extension.git
cd stochastic-sensor-placement-extension
git switch research-hardening
```

No version tags or release are claimed here. [Repository presentation notes](docs/repository_presentation.md)
contain the proposed About text and publication steps. The archived scientific
history remains available in `archive/` for baseline verification.
