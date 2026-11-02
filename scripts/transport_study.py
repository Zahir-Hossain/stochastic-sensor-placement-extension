"""Preregistered small-grid comparison of nominal, TV and transport ambiguity."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from stochplace import ForecastConfig, GaussianSensor, Problem, RepGrid, forecast, greedy, make_scenario
from stochplace.evaluate import score_on_truth
from stochplace.intensity import kde_intensity
from stochplace.optimize import Placement, swap_refine

if __package__:
    from .study_io import write_study
    from .transport_objective import TransportProblem, line_cost, transport_distance
else:
    from study_io import write_study
    from transport_objective import TransportProblem, line_cost, transport_distance

fm = import_module("stochplace.forecast")


def replicate(job):
    name, seed, settings = job
    scenario = make_scenario(name)
    history = scenario.history(8, np.random.default_rng(seed))
    grid = RepGrid(scenario.window, *settings["grid"])
    fine = RepGrid(scenario.window, *settings["evaluation_grid"])
    model = GaussianSensor(0.95, 1)
    config = ForecastConfig()
    candidates = scenario.window.grid(settings["candidate_spacing"])
    field = forecast(history, grid, 2, "stacked", config)
    nominal_problem = Problem(field, model)
    nominal = swap_refine(nominal_problem, candidates, greedy(nominal_problem, candidates, 4))
    alpha, p = grid.mesh()
    cost = line_cost(alpha[grid.mask], p[grid.mask], scenario.window)
    tv_errors, transport_errors, backtests = [], [], []
    for target in (5, 6, 7):
        prefix = history[: target - 1]
        predicted = forecast(prefix, grid, 2, "stacked", config)
        backtests.append(
            {
                "target": target,
                "history_epochs": len(prefix),
                "weight_fit": predicted.meta.get("weight_fit", "not_recorded"),
                "weight_fit_message": predicted.meta.get("weight_fit_message", ""),
            }
        )
        observed = kde_intensity(*history[target], grid, bandwidth=fm._bandwidth(prefix, config))
        first = predicted.mass[grid.mask] / predicted.total()
        second = observed.mass[grid.mask] / observed.total()
        tv_errors.append(0.5 * np.abs(first - second).sum())
        transport_errors.append(transport_distance(first, second, cost))
    tv_radius = float(np.quantile(tv_errors, settings["calibration_quantile"], method="higher"))
    radius = float(np.quantile(transport_errors, settings["calibration_quantile"], method="higher"))
    truth, true_fine = scenario.truth(grid, 9), scenario.truth(fine, 9)
    first, second = field.mass[grid.mask] / field.total(), truth.mass[grid.mask] / truth.total()
    distances = {"tv": 0.5 * np.abs(first - second).sum(), "w1": transport_distance(first, second, cost)}
    rows = []
    for kind, problem, bound_radius in (
        ("tv", Problem(field, model, "tv", radius=tv_radius), tv_radius),
        ("w1", TransportProblem(field, model, cost, radius), radius),
    ):
        start = Placement(
            nominal.sensors.copy(),
            problem.value(nominal.sensors),
            "nominal",
            meta={"indices": nominal.meta["indices"]},
        )
        a = swap_refine(problem, candidates, greedy(problem, candidates, 4))
        b = swap_refine(problem, candidates, start)
        robust = a if a.value <= b.value else b
        for label, plan in (("nominal_" + kind, start), (kind, robust)):
            certificate = 1 - problem.value(plan.sensors) / field.total()
            baseline = 1 - problem.value(nominal.sensors) / field.total()
            applies = bool(distances[kind] <= bound_radius)
            coarse = score_on_truth(plan.sensors, truth, model).detection_rate
            if applies and coarse < certificate - 1e-9:
                raise AssertionError("geometry-aware certificate failed on its own grid")
            rows.append(
                {
                    "scenario": name,
                    "seed": seed,
                    "method": label,
                    "detection_rate": score_on_truth(plan.sensors, true_fine, model).detection_rate,
                    "grid_detection_rate": coarse,
                    "certificate": certificate,
                    "certificate_applies": applies,
                    "radius": bound_radius,
                    "calibration_errors": json.dumps(tv_errors if kind == "tv" else transport_errors),
                    "calibration_backtests": json.dumps(backtests),
                    "truth_distance": distances[kind],
                    "weight_fit": field.meta.get("weight_fit", "not_recorded"),
                    "weight_fit_message": field.meta.get("weight_fit_message", ""),
                    "sensors_full": json.dumps(plan.sensors.tolist()),
                    "gain_vs_nominal_pp": 100
                    * (
                        score_on_truth(plan.sensors, true_fine, model).detection_rate
                        - score_on_truth(nominal.sensors, true_fine, model).detection_rate
                    ),
                    "calibration_origins": len(tv_errors),
                    "plan_changed": set(plan.meta["indices"]) != set(nominal.meta["indices"]),
                    "worst_case_gain_pp": 100 * (certificate - baseline),
                }
            )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--config", type=Path, default=Path("configs/research/transport_study.yaml"))
    parser.add_argument("--out", type=Path, default=Path("results/transport_geometry"))
    args = parser.parse_args()
    settings = yaml.safe_load(args.config.read_text())
    jobs = [(name, seed, settings) for name in settings["scenarios"] for seed in range(settings["seeds"])]
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        batches = list(executor.map(replicate, jobs))
    settings.update(
        {
            "study_id": "C5",
            "group_keys": ["scenario", "method"],
            "unique_keys": ["scenario", "seed", "method"],
            "expected_n": len(jobs) * 4,
            "metrics": [
                "detection_rate",
                "grid_detection_rate",
                "certificate",
                "certificate_applies",
                "plan_changed",
                "worst_case_gain_pp",
                "gain_vs_nominal_pp",
            ],
            "unit_interval": [
                "detection_rate",
                "grid_detection_rate",
                "certificate",
                "certificate_applies",
                "plan_changed",
            ],
            "scope": "Exploratory finite-grid certificates; three calibration errors do not establish nominal coverage.",
        }
    )
    write_study(
        args.out,
        pd.DataFrame([row for batch in batches for row in batch]),
        settings,
        ["scripts/transport_study.py", "scripts/transport_objective.py", str(args.config)],
    )


if __name__ == "__main__":
    main()
