"""Exploratory AIS controls with strictly training-only placement validation."""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import yaml
from scipy.optimize import minimize

from stochplace import ForecastConfig, GaussianSensor, Problem, RepGrid, forecast, solve
from stochplace.ais import AISStudyConfig, _epochs, extract_lines, read_gpkg_points
from stochplace.evaluate import score_on_lines

if __package__:
    from .study_io import write_study
else:
    from study_io import write_study

fm = import_module("stochplace.forecast")


def intensity_loss(weights, design, totals):
    combined = design @ weights
    count = max(len(design), 1)
    value = (float(totals @ weights) - float(np.log(combined).sum())) / count
    gradient = (totals - (design / combined[:, None]).sum(axis=0)) / count
    return value, gradient


def relative_ensemble(history, grid, method, config, ratio):
    records = fm._backtest_predictions(history, grid, 1, config.stack_models, config)
    if not records:
        raise ValueError("relative-floor fitting requires validation origins")
    values, totals = [], np.zeros(len(config.stack_models))
    for fields, alpha, p in records:
        ia, jp = grid.locate(alpha, p)
        keep = jp >= 0
        ia, jp = ia[keep], jp[keep]
        keep = grid.mask[ia, jp]
        floor = np.array([ratio * max(float(f.density[grid.mask].mean()), 1e-300) for f in fields])
        values.append(np.column_stack([f.density[ia[keep], jp[keep]] for f in fields]) + floor)
        totals += np.array([f.total() for f in fields])
    design = np.concatenate(values)
    scores = np.log(design).sum(axis=0) - totals
    weights = np.exp(scores - scores.max())
    weights /= weights.sum()
    status, message = "relative_floor_pseudo_bma", ""
    if method == "stacked":
        result = minimize(
            lambda w: intensity_loss(w, design, totals),
            np.full(len(totals), 1 / len(totals)),
            jac=True,
            method="SLSQP",
            bounds=[(0, 1)] * len(totals),
            constraints={"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones(len(totals))},
            options={"ftol": 1e-11, "maxiter": 500},
        )
        if result.success:
            weights = np.maximum(result.x, 0)
            weights /= weights.sum()
            status = "relative_floor_stacking"
        else:
            status, message = "fallback_pseudo_bma", str(result.message)
    return fm._combine_forecasts(
        history,
        grid,
        float(len(history)),
        config,
        fm._bandwidth(history, config),
        weights,
        method,
        {"weight_fit": status, "weight_fit_message": message},
    )


def policy_forecast(
    history, grid, method, config, scale=1.0, policy="original", min_origins=3, relative_floor=1e-6
):
    """Scale every nested prefix fit and keep all experimental policies explicit."""
    original_bandwidth = fm._bandwidth
    available = sum(
        target >= 3 for target in range(max(0, len(history) - config.backtest_epochs), len(history))
    )

    def scaled(prefix, cfg):
        return tuple(scale * value for value in original_bandwidth(prefix, cfg))

    with patch.object(fm, "_bandwidth", scaled):
        if (
            policy in ("minimum_origins", "both")
            and available < min_origins
            and method in ("stacked", "pseudo_bma")
        ):
            result = forecast(history, grid, 1, "pooled", config)
            result.meta.update(
                {
                    "weights": {m: float(m == "pooled") for m in config.stack_models},
                    "weight_fit": "minimum_origins_pooled",
                }
            )
        elif policy in ("relative_floor", "both") and available:
            result = relative_ensemble(history, grid, method, config, relative_floor)
        else:
            result = forecast(history, grid, 1, method, config)
    result.meta["backtest_origins"] = available if method in ("stacked", "pseudo_bma") else 0
    return result


def validation_scale(history, grid, model, candidates, method, scales, config, cache):
    losses = []
    for scale in scales:
        missed = count = 0.0
        for target in range(3, len(history)):
            alpha, p = history[target]
            if not len(alpha):
                continue
            key = (method, scale, target)
            if key not in cache:
                field = policy_forecast(history[:target], grid, method, config, scale)
                sensors = solve(Problem(field, model), candidates, 4, grid.window).sensors
                cache[key] = score_on_lines(sensors, alpha, p, model).detection_rate
            missed += (1 - cache[key]) * len(alpha)
            count += len(alpha)
        if count == 0:
            raise ValueError("no usable training placement validation")
        losses.append((missed / count, scale))
    return min(losses)[1], losses


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/raw/ais.gpkg"))
    parser.add_argument("--mode", choices=("bandwidth", "policies"), default="bandwidth")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    study = "ais_training_bandwidth" if args.mode == "bandwidth" else "ais_policy_ablation"
    args.config = args.config or Path("configs/research") / f"{study}.yaml"
    args.out = args.out or Path("results") / study
    settings = yaml.safe_load(args.config.read_text())
    data_sha = hashlib.sha256(args.data.read_bytes()).hexdigest()
    baseline_meta = json.loads(Path("results/ais_gothenburg/meta.json").read_text())
    assert data_sha == baseline_meta["data_sha256"], "different AIS input"
    cfg = AISStudyConfig()
    points = read_gpkg_points(args.data)
    origin = points.time.min().normalize()
    lines = extract_lines(points, cfg.window, epoch_hours=cfg.epoch_hours, epoch_origin=origin)
    epochs = _epochs(lines, cfg.epoch_hours, origin)
    grid = RepGrid(cfg.window, *cfg.grid_shape)
    model = GaussianSensor(cfg.sensor_rho, cfg.sensor_r_km)
    candidates = cfg.window.grid(cfg.candidate_spacing_km)
    config = ForecastConfig()
    reference = pd.read_csv("results/ais_gothenburg/runs.csv")
    reference = reference[reference.strategy == "pooled"].set_index("origin").detection_rate
    rows, validation, cache = [], [], {}
    for target in settings["origins"]:
        history = epochs[:target]
        alpha, p = epochs[target]
        for method in settings["methods"]:
            for policy in settings.get("policies", ["training_placement_cv"]):
                if args.mode == "bandwidth":
                    scale, losses = validation_scale(
                        history, grid, model, candidates, method, settings["scales"], config, cache
                    )
                    validation.extend(
                        {
                            "origin": target,
                            "method": method,
                            "scale": k,
                            "validation_miss_rate": loss,
                            "maximum_validation_target": target - 1,
                        }
                        for loss, k in losses
                    )
                else:
                    scale = 1.0
                field = policy_forecast(
                    history,
                    grid,
                    method,
                    config,
                    scale,
                    policy,
                    settings.get("minimum_validation_origins", 3),
                    settings.get("relative_floor", 1e-6),
                )
                plan = solve(Problem(field, model), candidates, cfg.n_sensors, cfg.window)
                rate = score_on_lines(plan.sensors, alpha, p, model).detection_rate
                rows.append(
                    {
                        "origin": target,
                        "method": method,
                        "policy": policy,
                        "detection_rate": rate,
                        "paired_gain_pp": 100 * (rate - reference.loc[target]),
                        "scale": scale,
                        "n_test": len(alpha),
                        "maximum_validation_target": target - 1,
                        "backtest_origins": field.meta["backtest_origins"],
                        "weight_fit": field.meta.get("weight_fit", "not_applicable"),
                        "weight_fit_message": field.meta.get("weight_fit_message", ""),
                        "weights": json.dumps(field.meta["weights"]) if "weights" in field.meta else None,
                    }
                )
        print(f"Completed training-only AIS origin {target}", flush=True)
    settings.update(
        {
            "study_id": "C4" if args.mode == "bandwidth" else "C6",
            "data_sha256": data_sha,
            "input_sha256": {
                "results/ais_gothenburg/runs.csv": hashlib.sha256(
                    Path("results/ais_gothenburg/runs.csv").read_bytes()
                ).hexdigest()
            },
            "group_keys": ["method", "policy"],
            "unique_keys": ["origin", "method", "policy"],
            "metrics": ["detection_rate", "paired_gain_pp"],
            "unit_interval": ["detection_rate"],
            "expected_n": len(settings["origins"])
            * len(settings["methods"])
            * len(settings.get("policies", ["training_placement_cv"])),
            "scope": "Exploratory reanalysis of previously viewed one-day test data; selection uses training only.",
        }
    )
    write_study(args.out, pd.DataFrame(rows), settings, ["scripts/ais_research.py", str(args.config)])
    if validation:
        pd.DataFrame(validation).to_csv(args.out / "validation.csv", index=False)


if __name__ == "__main__":
    main()
