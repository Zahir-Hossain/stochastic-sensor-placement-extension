# Open and run the project

This folder is the complete Git repository. It includes source, tests,
experiment configurations, generated results, figures and the technical report.
The original MATLAB version remains in `legacy/` and at tag `v0.1.0`.

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
| See what was corrected | `docs/review_notes.md` |
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

The working branch is `research-hardening`. The remote points to:

`https://github.com/Zahir-Hossain/stochastic-sensor-placement-extension.git`

Check the files, run the checks and review the commit history in VS Code's
Source Control panel. When ready to publish:

```bash
git status
git log --oneline --decorate -8
git push -u origin research-hardening
git push origin v0.1.0 v2.1.0
```

Open a pull request from `research-hardening` into `main` and let GitHub run
the CI workflow before merging. The archive contains local verification;
hosted CI results exist only after a push. No force push is needed.
