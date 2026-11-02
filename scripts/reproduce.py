"""Reproduce the research pipeline; write to output/reproduction by default.

Use --in-place to refresh tracked results and report inputs deliberately.
Use --seeds 2 --skip-ais for a small end-to-end run.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seeds", type=int)
    parser.add_argument("--skip-ais", action="store_true")
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument("--paper", action="store_true", help="also compile the report with latexmk")
    args = parser.parse_args()
    if args.workers < 1 or (args.seeds is not None and args.seeds < 1):
        parser.error("workers and seeds must be positive")
    if args.paper and args.skip_ais:
        parser.error("the complete report needs the AIS study; omit --skip-ais when using --paper")
    if args.paper and shutil.which("latexmk") is None:
        parser.error("install a LaTeX distribution providing latexmk to use --paper")
    root = Path(__file__).resolve().parents[1]
    dest = root if args.in_place else root / "output" / "reproduction"
    results, figures, paper = dest / "results", dest / "docs" / "figures", dest / "paper"
    paper.mkdir(parents=True, exist_ok=True)
    if not args.in_place:
        for name in ("main.tex", "refs.bib"):
            shutil.copy2(root / "paper" / name, paper / name)
    env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MPLBACKEND": "Agg"}

    def run(arguments: list[str], cwd: Path = root) -> None:
        print("\nRunning:", " ".join(arguments), flush=True)
        subprocess.run(arguments, cwd=cwd, env=env, check=True)

    configs = [
        str(root / "configs" / name)
        for name in (
            "suite_stationary.yaml",
            "suite_drift.yaml",
            "suite_lane_shift.yaml",
            "suite_emergence.yaml",
            "drift_sweep.yaml",
            "data_scarcity.yaml",
        )
    ]
    override = ["--seeds", str(args.seeds)] if args.seeds is not None else []
    run(
        [
            sys.executable,
            "-m",
            "stochplace.cli",
            "run",
            *configs,
            "--workers",
            str(args.workers),
            "--out",
            str(results),
            *override,
        ]
    )
    run(
        [
            sys.executable,
            "scripts/approximation_study.py",
            "--instances",
            str(3 if args.seeds is not None else 100),
            "--out",
            str(results / "approximation"),
        ]
    )
    run(
        [
            sys.executable,
            "-m",
            "stochplace.cli",
            "robustness",
            "--seeds",
            str(args.seeds if args.seeds is not None else 20),
            "--workers",
            str(args.workers),
            "--out",
            str(results / "robustness"),
            "--figures",
            str(figures),
        ]
    )
    if not args.skip_ais:
        run([sys.executable, "scripts/fetch_ais_sample.py"])
        run([sys.executable, "-m", "stochplace.cli", "ais", "--out", str(results / "ais_gothenburg")])
        run(
            [
                sys.executable,
                "scripts/ais_bandwidth_sensitivity.py",
                "--results",
                str(results),
                "--tables",
                str(dest / "docs" / "tables"),
                "--paper",
                str(paper),
                *(["--readme", str(root / "README.md")] if args.in_place else []),
            ]
        )
    run(
        [
            sys.executable,
            "scripts/void_failure_analysis.py",
            "--results",
            str(results),
            "--tables",
            str(dest / "docs" / "tables"),
            "--paper",
            str(paper),
            *(["--readme", str(root / "README.md")] if args.in_place else []),
        ]
    )
    run([sys.executable, "scripts/original_figures.py", "--results", str(results), "--out", str(figures)])
    run(
        [
            sys.executable,
            "scripts/make_tables.py",
            "--results",
            str(results),
            "--tables",
            str(dest / "docs" / "tables"),
            "--paper",
            str(paper),
        ]
    )
    run(
        [
            sys.executable,
            "scripts/research_summary.py",
            "--results",
            str(results),
            "--tables",
            str(dest / "docs" / "tables"),
            "--paper",
            str(paper),
            "--figures",
            str(figures),
            *(["--readme", str(root / "README.md")] if args.in_place else []),
        ]
    )
    run([sys.executable, "scripts/verify_artifacts.py", "--results", str(results)])
    if args.paper:
        run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], cwd=paper)
    print(f"\nFinished. Outputs: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
