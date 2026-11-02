"""Create an isolated environment and install this project for development.

Run with Python 3.10-3.13: ``python3 scripts/bootstrap.py``.
No Docker, database, credentials or external service is required.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--locked", action="store_true", help="use the tested Python 3.12 dependency snapshot"
    )
    args = parser.parse_args()
    if not (3, 10) <= sys.version_info[:2] <= (3, 13):
        parser.error("use Python 3.10-3.13; Python 3.12 is the reference environment")
    if args.locked and sys.version_info[:2] != (3, 12):
        parser.error("--locked requires Python 3.12")
    root = Path(__file__).resolve().parents[1]
    environment = root / ".venv"
    if not environment.exists():
        venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if args.locked:
        subprocess.run(
            [str(python), "-m", "pip", "install", "-r", "requirements/reproduce-py312.txt"],
            cwd=root,
            check=True,
        )
    build_mode = ["--no-build-isolation"] if args.locked else []
    subprocess.run(
        [str(python), "-m", "pip", "install", *build_mode, "-e", ".[dev,lint]"], cwd=root, check=True
    )
    print("\nReady. In VS Code select the .venv interpreter, then run the Verify project task.")
    print(f"Terminal check: {python} scripts/check.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
