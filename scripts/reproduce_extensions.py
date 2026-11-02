"""Reproduce the frozen research extension, including original-study regression checks."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--skip-baseline", action="store_true", help="resume after a verified baseline regeneration"
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("workers must be positive")
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MPLBACKEND": "Agg"}
    baseline = json.loads(Path("docs/part_c_baseline.json").read_text())["pre_c_commit"]

    def run(*command: str) -> None:
        print("\nRunning:", " ".join(command), flush=True)
        subprocess.run(command, env=env, check=True)

    if not args.skip_baseline:
        run(
            sys.executable,
            "scripts/reproduce.py",
            "--workers",
            str(args.workers),
            "--in-place",
            "--defer-verification",
        )
    run(sys.executable, "scripts/compare_summaries.py", "--base", baseline)
    run(
        sys.executable,
        "-m",
        "stochplace.cli",
        "run",
        *(str(path) for path in sorted(Path("configs").glob("holdout_*.yaml"))),
        "--workers",
        str(args.workers),
        "--out",
        "results",
    )
    run(sys.executable, "scripts/sampler_study.py", "--workers", str(args.workers))
    run(sys.executable, "scripts/ais_research.py", "--mode", "bandwidth")
    run(sys.executable, "scripts/ais_research.py", "--mode", "policies")
    run(sys.executable, "scripts/transport_study.py", "--workers", str(args.workers))
    run(sys.executable, "scripts/research_extensions_summary.py")
    run("latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-cd", "paper/main.tex")
    run(sys.executable, "scripts/verify_artifacts.py")
    run(sys.executable, "scripts/check.py", "--full")
    print("\nResearch reproduction complete. C7 remains blocked by raw archive access.", flush=True)


if __name__ == "__main__":
    main()
