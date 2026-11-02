"""Run local quality checks and write a machine-readable execution record."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="include statistical and available Octave checks")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MPLBACKEND": "Agg"}
    checks = [
        [sys.executable, "-m", "ruff", "check", "src", "tests", "scripts", "examples"],
        [sys.executable, "-m", "ruff", "format", "--check", "src", "tests", "scripts", "examples"],
        [sys.executable, "-m", "mypy"],
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=stochplace",
            "--cov-report=term-missing",
            *([] if args.full else ["-m", "not slow and not octave"]),
        ],
        [sys.executable, "examples/quickstart.py"],
    ]
    records = []
    for command in checks:
        print("\nRunning:", " ".join(command), flush=True)
        started = time.monotonic()
        result = subprocess.run(command, cwd=root, env=env, check=False)
        records.append(
            {
                "command": command[1:],
                "exit_code": result.returncode,
                "duration_seconds": round(time.monotonic() - started, 2),
            }
        )
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "full": args.full,
        "octave_available": shutil.which("octave") is not None,
        "checks": records,
        "passed": all(r["exit_code"] == 0 for r in records),
    }
    (root / "validation.local.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "\nAll requested checks passed."
        if report["passed"]
        else "\nSome checks failed; inspect output above."
    )
    if args.full and not report["octave_available"]:
        print(
            "Octave parity is skipped locally because Octave is unavailable; CI has a dedicated parity job."
        )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
