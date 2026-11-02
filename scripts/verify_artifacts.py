"""Check result provenance, run uniqueness, summaries and risk certificates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from packaging.version import Version

from stochplace.experiment import _source_hash, summarise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    args = parser.parse_args()
    current = _source_hash()
    folders = sorted(path.parent for path in args.results.glob("*/meta.json"))
    if not folders:
        raise ValueError("no result provenance found")
    for folder in folders:
        meta = json.loads((folder / "meta.json").read_text())
        if meta.get("source_sha256") != current:
            raise ValueError(f"{folder}: source fingerprint differs; regenerate its results")
        # Preserve binary64 values across CSV round trips. The default
        # parser can flip the sign of differences at numerical ties,
        # changing a win count even when means agree to machine precision.
        if Version(pd.__version__).release[:2] >= (3, 1):
            runs = pd.read_csv(folder / "runs.csv")
        else:
            runs = pd.read_csv(folder / "runs.csv", float_precision="round_trip")
        if meta.get("study_kind") == "preregistered_research":
            from study_io import verify_study

            verify_study(folder, meta)
            print(f"OK {folder.name}: {len(runs)} preregistered research runs")
            continue
        if folder.name == "ais_bandwidth_sensitivity":
            from ais_bandwidth_sensitivity import DISCLOSURE, SCALES, STRATEGIES, summarise_sensitivity

            script = Path(__file__).resolve().with_name("ais_bandwidth_sensitivity.py")
            assert meta["script_sha256"] == hashlib.sha256(script.read_bytes()).hexdigest()
            assert meta["disclosure"] == DISCLOSURE
            assert tuple(meta["scales"]) == SCALES
            assert tuple(meta["strategies"]) == STRATEGIES
            assert not runs.duplicated(["scale", "origin", "strategy"]).any()
            baseline_folder = args.results / "ais_gothenburg"
            baseline_meta = json.loads((baseline_folder / "meta.json").read_text())
            assert meta["data_sha256"] == baseline_meta["data_sha256"]
            baseline_runs = pd.read_csv(baseline_folder / "runs.csv")
            origins = sorted(baseline_runs.origin.unique())
            expected_index = pd.MultiIndex.from_product([SCALES, origins, STRATEGIES])
            actual_index = pd.MultiIndex.from_frame(runs[["scale", "origin", "strategy"]])
            assert set(actual_index) == set(expected_index), "missing sensitivity runs"
            expected = summarise_sensitivity(runs).set_index(["scale", "strategy"]).sort_index()
            actual = pd.read_csv(folder / "summary.csv").set_index(["scale", "strategy"]).sort_index()
            pd.testing.assert_frame_equal(actual, expected, check_exact=False, rtol=1e-9, atol=1e-10)
            baseline = pd.read_csv(baseline_folder / "summary.csv").set_index("strategy")
            default = actual.loc[1.0]
            for column in ("mean_over_origins", "pooled_detection_rate", "n_origins"):
                np.testing.assert_allclose(
                    default[column], baseline.loc[default.index, column], rtol=0, atol=1e-9
                )
            original = baseline_runs[baseline_runs.strategy.isin(STRATEGIES)].set_index(
                ["origin", "strategy"]
            )
            repeated = runs[runs.scale == 1.0].set_index(["origin", "strategy"]).loc[original.index]
            np.testing.assert_allclose(repeated.detection_rate, original.detection_rate, rtol=0, atol=1e-9)
            print(f"OK {folder.name}: {len(runs)} runs; default scale matches published AIS")
            continue
        if folder.name == "approximation":
            script = Path(__file__).resolve().with_name("approximation_study.py")
            if meta["script_sha256"] != hashlib.sha256(script.read_bytes()).hexdigest():
                raise ValueError("approximation script fingerprint differs")
            assert len(runs) == meta["instances"]
            assert (runs.ratio >= 1 - 1 / np.e - 1e-10).all()
        elif folder.name == "robustness":
            covered = runs[runs.certificate_applies_on_grid]
            assert (covered.grid_detection_rate >= covered.worst_case_detection_rate - 1e-9).all()
            assert not runs.duplicated(["scenario", "seed", "radius", "strategy"]).any()
        elif folder.name == "ais_gothenburg":
            assert not runs.duplicated(["origin", "strategy"]).any()
            lines = pd.read_csv(folder / "lines.csv", parse_dates=["start_time", "end_time"])
            hours = meta["config"]["epoch_hours"]
            nanoseconds = round(hours * 3600 * 1e9)
            origin_ns = pd.Timestamp(meta["epoch_origin"]).value
            start = (lines.start_time.dt.as_unit("ns").astype("int64") - origin_ns) // nanoseconds
            end = (lines.end_time.dt.as_unit("ns").astype("int64") - origin_ns) // nanoseconds
            assert (start == end).all(), "a line fit crosses a validation epoch boundary"
        else:
            cfg = meta["config"]
            assert not runs.duplicated(["setting_id", "seed", "horizon", "strategy"]).any()
            assert len(runs) == meta["n_replicates"] * len(cfg["strategies"])
            encoded = json.dumps(cfg, sort_keys=True, default=str).encode()
            assert meta["config_sha256"] == hashlib.sha256(encoded).hexdigest()[:16]
            actual = pd.read_csv(folder / "summary.csv")
            expected = summarise(runs)
            keys = [c for c in expected.columns if c.startswith("param_")] + ["horizon", "strategy"]
            actual = actual.sort_values(keys).reset_index(drop=True)
            expected = expected.sort_values(keys).reset_index(drop=True)
            for column in expected.select_dtypes(include="number").columns:
                np.testing.assert_allclose(
                    actual[column],
                    expected[column],
                    rtol=1e-9,
                    atol=1e-10,
                    equal_nan=True,
                    err_msg=f"{folder}: {column}",
                )
        if "detection_rate" in runs:
            assert np.isfinite(runs.detection_rate).all()
            assert runs.detection_rate.between(-1e-12, 1 + 1e-12).all()
        print(f"OK {folder.name}: {len(runs)} runs")
    print(f"All {len(folders)} result sets match source {current[:12]}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
