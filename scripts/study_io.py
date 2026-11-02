"""Provenance and raw-to-summary verification for preregistered research runners."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from stochplace.experiment import _dependency_versions, _git_commit, _source_hash


def summarise_study(runs: pd.DataFrame, config: dict) -> pd.DataFrame:
    keys, metrics = config["group_keys"], config["metrics"]
    if runs.duplicated(config["unique_keys"]).any():
        raise ValueError("duplicate research run keys")
    if not np.isfinite(runs[metrics].to_numpy(dtype=float)).all():
        raise ValueError("non-finite research metrics")
    if "expected_n" in config and len(runs) != config["expected_n"]:
        raise ValueError("incomplete research runs")
    summary = runs.groupby(keys, sort=True, dropna=False)[metrics].mean().reset_index()
    summary["n"] = runs.groupby(keys, sort=True, dropna=False).size().to_numpy()
    return summary


def write_study(out: Path, runs: pd.DataFrame, config: dict, scripts: list[str]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    runs.to_csv(out / "runs.csv", index=False)
    summarise_study(runs, config).to_csv(out / "summary.csv", index=False)
    files = [*scripts, "scripts/study_io.py", "docs/preregistration.md"]
    meta = {
        "study_kind": "preregistered_research",
        "source_sha256": _source_hash(),
        "git_commit": _git_commit(),
        "config": config,
        "dependencies": _dependency_versions(),
        "file_sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in files},
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2, default=str) + "\n")


def verify_study(folder: Path, meta: dict) -> None:
    for name, digest in meta["file_sha256"].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, f"{folder}: {name} fingerprint"
    runs = pd.read_csv(folder / "runs.csv")
    config = meta["config"]
    for name, digest in config.get("input_sha256", {}).items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, f"{folder}: input {name}"
    expected = summarise_study(runs, config)
    actual = pd.read_csv(folder / "summary.csv")
    keys = config["group_keys"]
    pd.testing.assert_frame_equal(
        actual.sort_values(keys).reset_index(drop=True),
        expected.sort_values(keys).reset_index(drop=True),
        check_exact=False,
        rtol=1e-9,
        atol=1e-10,
    )
    for column in config.get("unit_interval", []):
        assert runs[column].between(-1e-12, 1 + 1e-12).all(), f"{folder}: {column} outside [0,1]"
    if "certificate_applies" in runs:
        covered = runs[runs.certificate_applies]
        assert (covered.grid_detection_rate >= covered.certificate - 1e-9).all(), (
            "transport certificate failed"
        )
    if "weights" in runs:
        for value in runs.weights.dropna():
            weights = np.asarray(list(json.loads(value).values()), dtype=float)
            assert np.isfinite(weights).all() and (weights >= 0).all()
            assert abs(weights.sum() - 1) < 1e-9

    if "maximum_validation_target" in runs:
        assert (runs.maximum_validation_target < runs.origin).all(), "AIS validation reaches test origin"
    if (folder / "validation.csv").exists():
        validation = pd.read_csv(folder / "validation.csv")
        assert (validation.maximum_validation_target < validation.origin).all()
        for (origin, method), group in validation.groupby(["origin", "method"]):
            selected = group.sort_values(["validation_miss_rate", "scale"]).iloc[0].scale
            assert (runs[(runs.origin == origin) & (runs.method == method)].scale == selected).all()
    if "calibration_errors" in runs:
        for _, row in runs.iterrows():
            errors = np.asarray(json.loads(row.calibration_errors))
            assert len(errors) == row.calibration_origins
            np.testing.assert_allclose(
                row.radius,
                np.quantile(errors, config["calibration_quantile"], method="higher"),
                rtol=0,
                atol=1e-10,
            )
    if "gate" in config:
        gate = config["gate"]
        reported = json.loads((folder / "gate.json").read_text())
        assert reported["adopted"] is False
        for method, stated in reported["eligible_for_further_study"].items():
            sub = expected[expected.method == method]
            passes = bool(
                len(sub) == len(config["scenarios"])
                and sub.sample_covered_90.ge(gate["min_coverage"]).all()
                and sub.sample_rank.between(gate["min_mean_rank"], gate["max_mean_rank"]).all()
                and sub.sample_mean_relative_l1.le(gate["max_mean_mismatch"]).all()
            )
            assert stated == passes, "sampler gate disagrees with its frozen criteria"
