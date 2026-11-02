"""Evaluate frozen candidate laws on preregistered out-of-family expected-loss plans."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from stochplace import ForecastConfig, Problem, RepGrid, forecast, make_scenario
from stochplace.experiment import load_config, sample_diagnostics
from stochplace.sensors import sensor_from_config

if __package__:
    from .research_samplers import residual_candidate, weighted_candidate
    from .study_io import write_study
else:
    from research_samplers import residual_candidate, weighted_candidate
    from study_io import write_study


def replicate(job: tuple[str, int]) -> list[dict]:
    name, seed = job
    cfg = load_config(f"configs/holdout_{name}.yaml")
    scenario = make_scenario(name, scenario_seed=seed)
    history = scenario.history(cfg.history_epochs, np.random.default_rng([seed, 0, 2]))
    grid = RepGrid(scenario.window, **cfg.grid)
    config = ForecastConfig(**cfg.forecast)
    current = forecast(history, grid, 2, "stacked", config)
    runs = pd.read_csv(f"results/holdout_{name}/runs.csv")
    saved = runs[(runs.seed == seed) & (runs.strategy == "stacked")].iloc[0]
    sensors = np.asarray(json.loads(saved.sensors_full))
    truth = scenario.truth(grid, cfg.history_epochs - 1 + 2)
    model = sensor_from_config(cfg.sensor)
    true_loss = float(Problem(truth, model).lambda_miss(sensors))
    np.testing.assert_allclose(true_loss, saved.sample_true_loss, rtol=0, atol=1e-9)
    candidates = [
        current,
        weighted_candidate(history, grid, 2, config, current, seed),
        residual_candidate(history, grid, 2, config, current, seed),
    ]
    rows = []
    for method, field in zip(("component", "weighted_candidate", "residual_candidate"), candidates):
        problem = Problem(field, model)
        losses = np.asarray(problem.lambda_miss(sensors, per_sample=True))
        row = {"scenario": name, "seed": seed, "method": method, **sample_diagnostics(losses, true_loss)}
        row["sample_mean_relative_l1"] = float(
            np.abs(field.sample_mass.mean(axis=0) - field.mass).sum() / field.total()
        )
        row["weight_fit"] = current.meta.get("weight_fit", "not_recorded")
        row["weight_fit_message"] = current.meta.get("weight_fit_message", "")
        row["residual_backtests"] = json.dumps(field.meta.get("residual_backtests", []))
        if method == "component":
            np.testing.assert_allclose(row["sample_rank"], saved.sample_rank, rtol=0, atol=1e-12)
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--config", type=Path, default=Path("configs/research/sampler_candidates.yaml"))
    parser.add_argument("--out", type=Path, default=Path("results/sampler_calibration"))
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text())
    assert "sample_rank" in pd.read_csv("results/suite_drift/runs.csv", nrows=0), "complete C2 first"
    jobs = [(name, seed) for name in config["scenarios"] for seed in range(config["seeds"])]
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        batches = list(executor.map(replicate, jobs))
    runs = pd.DataFrame([row for batch in batches for row in batch])
    config.update(
        {
            "study_id": "C3",
            "group_keys": ["scenario", "method"],
            "unique_keys": ["scenario", "seed", "method"],
            "metrics": ["sample_rank", "sample_covered_90", "sample_mean_relative_l1"],
            "unit_interval": ["sample_rank", "sample_covered_90"],
            "expected_n": len(jobs) * 3,
            "input_sha256": {
                f"results/holdout_{name}/runs.csv": hashlib.sha256(
                    Path(f"results/holdout_{name}/runs.csv").read_bytes()
                ).hexdigest()
                for name in config["scenarios"]
            },
        }
    )
    write_study(
        args.out, runs, config, ["scripts/sampler_study.py", "scripts/research_samplers.py", str(args.config)]
    )
    summary = pd.read_csv(args.out / "summary.csv")
    gate = config["gate"]
    eligible = {}
    for method in ("weighted_candidate", "residual_candidate"):
        sub = summary[summary.method == method]
        eligible[method] = bool(
            len(sub) == len(config["scenarios"])
            and sub.sample_covered_90.ge(gate["min_coverage"]).all()
            and sub.sample_rank.between(gate["min_mean_rank"], gate["max_mean_rank"]).all()
            and sub.sample_mean_relative_l1.le(gate["max_mean_mismatch"]).all()
        )
    (args.out / "gate.json").write_text(
        json.dumps(
            {
                "eligible_for_further_study": eligible,
                "adopted": False,
                "scope": "Latent expected-loss diagnostics only; no full predictive-law calibration claim.",
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(eligible, indent=2))


if __name__ == "__main__":
    main()
