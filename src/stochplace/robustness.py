"""Forecast stress tests and finite-grid total-variation robustness.

All outer planners use the same candidate grid and one-sensor exchange
search. The TV inner problem is exact; the outer search is a heuristic.
The nominal total is fixed within each adversarial problem. Certificates
for detection fractions apply only to the discretised, normalised truth
when it lies inside the declared TV ball.
"""

from __future__ import annotations

import json
import platform
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .evaluate import bootstrap_ci, score_on_truth
from .experiment import _dependency_versions, _git_commit, _source_hash
from .forecast import ForecastConfig, forecast
from .grid import RepGrid
from .objective import Problem
from .optimize import Placement, greedy, swap_refine
from .scenarios import make_scenario
from .sensors import GaussianSensor


@dataclass(frozen=True)
class RobustnessConfig:
    seeds: int = 20
    scenarios: tuple[str, ...] = ("stationary", "drift", "lane_shift", "emergence", "reversal", "seam_drift")
    radii: tuple[float, ...] = (0.0, 0.05, 0.15)
    horizon: int = 2
    history_epochs: int = 8
    grid_shape: tuple[int, int] = (72, 48)
    eval_grid_shape: tuple[int, int] = (216, 144)
    candidate_spacing: float = 2.5
    n_sensors: int = 4


def _replicate(args: tuple[RobustnessConfig, str, int]) -> list[dict[str, Any]]:
    cfg, name, seed = args
    scenario = make_scenario(name)
    rng = np.random.default_rng(seed)
    history = scenario.history(cfg.history_epochs, rng)
    t_star = cfg.history_epochs - 1 + cfg.horizon
    grid = RepGrid(scenario.window, *cfg.grid_shape)
    fine = RepGrid(scenario.window, *cfg.eval_grid_shape)
    truth = scenario.truth(grid, t_star)
    true_fine = scenario.truth(fine, t_star)
    sensor = GaussianSensor(0.95, 1.0)
    candidates = scenario.window.grid(cfg.candidate_spacing)
    fcfg = ForecastConfig(n_samples=16)
    fields = {
        name_: forecast(history, grid, cfg.horizon, name_, fcfg)
        for name_ in ("pooled", "stacked", "pseudo_bma")
    }
    plans = {}
    for method, field in fields.items():
        problem = Problem(field, sensor)
        plans[method] = swap_refine(problem, candidates, greedy(problem, candidates, cfg.n_sensors))
    rows = []
    for radius in cfg.radii:
        robust = Problem(fields["stacked"], sensor, "tv", radius=radius)
        greedy_plan = swap_refine(robust, candidates, greedy(robust, candidates, cfg.n_sensors))
        nominal = plans["stacked"]
        nominal_start = Placement(
            nominal.sensors.copy(),
            robust.value(nominal.sensors),
            "nominal_stacked",
            meta={"indices": nominal.meta["indices"]},
        )
        nominal_plan = swap_refine(robust, candidates, nominal_start)
        robust_plan = nominal_plan if nominal_plan.value < greedy_plan.value else greedy_plan
        robust_plan.meta["start_won"] = "nominal_stacked" if robust_plan is nominal_plan else "tv_greedy"
        choices = {**plans, "stacked_tv": robust_plan}
        for method, plan in choices.items():
            field = fields["stacked"] if method == "stacked_tv" else fields[method]
            risk = Problem(field, sensor, "tv", radius=radius)
            total = field.total()
            distance = 0.5 * float(np.abs(truth.mass / truth.total() - field.mass / total).sum())
            worst_detection = 1 - risk.value(plan.sensors) / total
            coarse_detection = score_on_truth(plan.sensors, truth, sensor).detection_rate
            fine_detection = score_on_truth(plan.sensors, true_fine, sensor).detection_rate
            covered = distance <= radius + 1e-12
            if covered and coarse_detection < worst_detection - 1e-9:
                raise AssertionError("TV certificate violated on its own evaluation grid")
            rows.append(
                {
                    "scenario": name,
                    "seed": seed,
                    "horizon": cfg.horizon,
                    "radius": radius,
                    "strategy": method,
                    "detection_rate": fine_detection,
                    "grid_detection_rate": coarse_detection,
                    "nominal_detection_rate": score_on_truth(plan.sensors, field, sensor).detection_rate,
                    "worst_case_detection_rate": worst_detection,
                    "truth_tv_distance": distance,
                    "certificate_applies_on_grid": bool(covered),
                    "discretisation_error_pp": 100 * (fine_detection - coarse_detection),
                    "sensors": json.dumps(plan.sensors.tolist()),
                    "tv_start": robust_plan.meta["start_won"] if method == "stacked_tv" else "",
                    "weight_fit": field.meta.get("weight_fit", "not_applicable"),
                    "weight_fit_message": field.meta.get("weight_fit_message", ""),
                }
            )
    return rows


def run_robustness(out: Path, cfg: RobustnessConfig | None = None, workers: int = 2) -> pd.DataFrame:
    """Write runs, paired summaries, provenance and figures for the study."""
    cfg = cfg or RobustnessConfig()
    if cfg.seeds < 1 or workers < 1 or not cfg.scenarios or not cfg.radii:
        raise ValueError("positive seeds/workers and nonempty scenarios/radii required")
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(cfg, name, seed) for name in cfg.scenarios for seed in range(cfg.seeds)]
    if workers == 1:
        batches = list(map(_replicate, jobs))
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            batches = list(executor.map(_replicate, jobs))
    runs = pd.DataFrame([row for batch in batches for row in batch])
    runs.to_csv(out / "runs.csv", index=False)
    summary = []
    for (scenario, radius, method), group in runs.groupby(["scenario", "radius", "strategy"], sort=False):
        base = runs[
            (runs.scenario == scenario) & (runs.radius == radius) & (runs.strategy == "stacked")
        ].set_index("seed")
        current = group.set_index("seed")
        gain = 100 * (current.detection_rate - base.detection_rate)
        robust_gain = 100 * (current.worst_case_detection_rate - base.worst_case_detection_rate)
        mean, lo, hi = bootstrap_ci(gain.to_numpy())
        summary.append(
            {
                "scenario": scenario,
                "radius": radius,
                "strategy": method,
                "n": len(group),
                "detection_rate_mean": float(group.detection_rate.mean()),
                "worst_case_detection_rate_mean": float(group.worst_case_detection_rate.mean()),
                "gain_vs_stacked_pp": mean,
                "gain_lo": lo,
                "gain_hi": hi,
                "worst_case_gain_vs_stacked_pp": float(robust_gain.mean()),
                "fraction_truth_inside_ball": float(group.certificate_applies_on_grid.mean()),
                "max_abs_discretisation_error_pp": float(group.discretisation_error_pp.abs().max()),
            }
        )
    pd.DataFrame(summary).to_csv(out / "summary.csv", index=False)
    meta = {
        "config": asdict(cfg),
        "source_sha256": _source_hash(),
        "git_commit": _git_commit(),
        "python": platform.python_version(),
        "dependencies": _dependency_versions(),
        "certificate_scope": "normalised cell masses on planning grid, only if truth lies in TV ball",
        "outer_optimisation": "greedy plus exact one-sensor exchanges; no global guarantee",
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    return runs


def plot_robustness(results: Path, out: Path) -> None:
    """Nominal/worst-case tradeoff and an intentionally unforecastable shift."""
    import matplotlib.pyplot as plt

    from .figures import INK2, _save, _style

    _style()
    summary = pd.read_csv(results / "summary.csv")
    names = list(summary.scenario.unique())
    fig, axes = plt.subplots(2, 3, figsize=(12, 7.2), sharex=True, sharey=True)
    for ax, name in zip(axes.ravel(), names):
        for method, colour in (("stacked", "#2a78d6"), ("stacked_tv", "#773aa6")):
            sub = summary[(summary.scenario == name) & (summary.strategy == method)].sort_values("radius")
            title = "forecast plan" if method == "stacked" else "TV robust plan"
            ax.plot(sub.radius, 100 * sub.detection_rate_mean, "o-", color=colour, label=title + ": future")
            ax.plot(
                sub.radius,
                100 * sub.worst_case_detection_rate_mean,
                "s--",
                color=colour,
                alpha=0.7,
                label=title + ": worst case",
            )
        ax.set_title(name.replace("_", " "), loc="left")
        ax.set_xlabel("TV radius (fraction of mass)")
        ax.set_ylabel("expected detection (%)")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle(
        "Robustness is a tradeoff, not a promise of better forecasts", x=0.08, ha="left", fontsize=15
    )
    fig.text(
        0.08,
        0.915,
        "Solid: fine-grid future. Dashed: exact adversarial loss on the planning grid. "
        "All planners use the same candidate grid.",
        color=INK2,
        fontsize=9,
    )
    fig.subplots_adjust(top=0.86, bottom=0.18, hspace=0.42, wspace=0.25)
    _save(fig, out, "robustness_frontier")
