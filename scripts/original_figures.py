"""Render the original report against its fixed study population."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from stochplace.figures import make_all

ORIGINAL_STUDIES = (
    "suite_stationary",
    "suite_drift",
    "suite_lane_shift",
    "suite_emergence",
    "drift_sweep",
    "data_scarcity",
    "approximation",
    "robustness",
    "ais_gothenburg",
    "ais_bandwidth_sensitivity",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--out", type=Path, default=Path("docs/figures"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="stochplace-report-") as folder:
        view = Path(folder)
        for name in ORIGINAL_STUDIES:
            source = args.results / name
            if source.exists():
                (view / name).symlink_to(source.resolve(), target_is_directory=True)
        make_all(view, args.out)
        shutil.copyfile(view / "figure_stats.json", args.results / "figure_stats.json")


if __name__ == "__main__":
    main()
