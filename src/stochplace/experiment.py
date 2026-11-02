"""Config-driven Monte Carlo experiments.

An experiment config (YAML) names a scenario, a parameter sweep, the
planning strategies and the number of seeds. Every replicate draws a
history, lets each strategy plan a placement from that history alone,
and scores all placements against the *same* true future intensity.

Strategy names
--------------
``<source>`` or ``<source>:<objective>`` where ``source`` is a
forecaster name (see :mod:`stochplace.forecast`), ``lgcp`` (LGCP fitted
to the pooled history), ``oracle`` (true future intensity), ``fence``
or ``random``; and ``objective`` is ``expected`` (default), ``void`` or
``cvar``.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import platform
import subprocess
import time
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from . import __version__
from ._typing import FloatArray
from .evaluate import bootstrap_ci, score_on_lines, score_on_truth
from .forecast import FORECASTERS, ForecastConfig, _bandwidth, forecast
from .geometry import Window
from .grid import IntensityField, RepGrid
from .intensity import lgcp_intensity
from .objective import Problem
from .optimize import fence_placement, random_placement, solve
from .scenarios import Scenario, make_scenario
from .sensors import sensor_from_config

__all__ = ["ExperimentConfig", "load_config", "run_experiment", "run_replicate", "summarise"]


@dataclass
class ExperimentConfig:
    name: str
    scenario: str
    sweep: dict[str, list[Any]] = field(default_factory=dict)
    scenario_params: dict[str, Any] = field(default_factory=dict)
    history_epochs: int = 8
    horizons: list[int] = field(default_factory=lambda: [2])
    seeds: int = 40
    seed_offset: int = 0
    vary_scenario_seed: bool = False
    n_sensors: int = 4
    sensor: dict[str, Any] = field(default_factory=lambda: {"type": "gaussian", "rho": 0.95, "r": 1.0})
    grid: dict[str, int] = field(default_factory=lambda: {"n_alpha": 120, "n_p": 64})
    eval_grid: dict[str, int] = field(default_factory=lambda: {"n_alpha": 360, "n_p": 192})
    lgcp_fit_shape: list[int] = field(default_factory=lambda: [60, 32])
    candidate_spacing: float = 1.0
    refine: bool = True
    beta: float = 0.9
    radius: float = 0.05
    n_test_epochs: int = 1
    strategies: list[str] = field(default_factory=lambda: ["pooled", "drift", "oracle"])
    forecast: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def settings(self) -> list[dict[str, Any]]:
        keys = sorted(self.sweep)
        if not keys:
            return [{}]
        return [dict(zip(keys, vals)) for vals in itertools.product(*(self.sweep[k] for k in keys))]

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def load_config(path: str | Path) -> ExperimentConfig:
    import yaml

    with open(path) as fh:
        raw = yaml.safe_load(fh)
    return ExperimentConfig(**raw)


# ----------------------------------------------------------------------
def _parse_strategy(name: str) -> tuple[str, str]:
    src, _, obj = name.partition(":")
    return src, (obj or "expected")


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True, timeout=5
        )
        # "dirty" means uncommitted changes to code or configs, not to outputs
        dirty = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "--untracked-files=no",
                "--",
                "src",
                "configs",
                "scripts",
                "pyproject.toml",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")
    except Exception:  # pragma: no cover - git not available
        return "unknown"


def run_replicate(
    cfg: ExperimentConfig, setting: dict[str, Any], setting_id: int, horizon: int, seed: int
) -> list[dict[str, Any]]:
    """Run every strategy on one simulated history."""
    rng = np.random.default_rng([seed, setting_id, horizon])
    params = {**cfg.scenario_params, **setting}
    if cfg.vary_scenario_seed:
        params["scenario_seed"] = seed
    rate = params.pop("rate", None)
    sc: Scenario = make_scenario(cfg.scenario, **params)
    if rate is not None:
        sc = sc.with_rate(float(rate))
    window: Window = sc.window
    model = sensor_from_config(cfg.sensor)
    gp = RepGrid(window, **cfg.grid)
    ge = RepGrid(window, **cfg.eval_grid)
    T = cfg.history_epochs
    t_star = float(T - 1 + horizon)
    history = sc.history(T, rng)
    truth_p = sc.truth(gp, t_star)
    truth_e = sc.truth(ge, t_star)
    test_a, test_p = [], []
    for _ in range(cfg.n_test_epochs):
        a, p = sc.sample(t_star, rng)
        test_a.append(a)
        test_p.append(p)
    ta, tp = np.concatenate(test_a), np.concatenate(test_p)
    fcfg = ForecastConfig(**cfg.forecast)
    bw = _bandwidth(history, fcfg)
    cand = window.grid(cfg.candidate_spacing)

    oracle_prob = Problem(truth_p, model)
    oracle = solve(oracle_prob, cand, cfg.n_sensors, window, do_refine=cfg.refine)
    oracle_e = score_on_truth(oracle.sensors, truth_e, model)

    cache: dict[str, IntensityField] = {}

    def get_field(src: str) -> IntensityField | None:
        if src in cache:
            return cache[src]
        if src == "oracle":
            f: IntensityField | None = truth_p
        elif src in ("fence", "random"):
            f = None
        elif src == "lgcp":
            a = np.concatenate([h[0] for h in history])
            p = np.concatenate([h[1] for h in history])
            f = lgcp_intensity(
                a,
                p,
                gp,
                n_epochs=T,
                fit_shape=(int(cfg.lgcp_fit_shape[0]), int(cfg.lgcp_fit_shape[1])),
                rng=np.random.default_rng(seed),  # type: ignore[arg-type]
            ).field
        elif src in FORECASTERS:
            f = forecast(history, gp, horizon, src, fcfg, bw)
        else:
            raise KeyError(f"unknown strategy source {src!r}")
        if f is not None:
            cache[src] = f
        return f

    rows: list[dict[str, Any]] = []
    for strat in cfg.strategies:
        src, obj = _parse_strategy(strat)
        t0 = time.perf_counter()
        f = get_field(src)
        if src == "oracle" and obj == "expected":
            pl = oracle
            plan_prob = oracle_prob
        elif f is None:
            plan_prob = oracle_prob  # only used for value bookkeeping
            if src == "fence":
                pl = fence_placement(plan_prob, window, cfg.n_sensors)
            else:
                pl = random_placement(plan_prob, window, cfg.n_sensors, np.random.default_rng([seed, 99]))
        else:
            plan_prob = Problem(f, model, objective=obj, beta=cfg.beta, radius=cfg.radius)
            pl = solve(plan_prob, cand, cfg.n_sensors, window, do_refine=cfg.refine)
        elapsed = time.perf_counter() - t0
        s_e = score_on_truth(pl.sensors, truth_e, model)
        s_p = score_on_truth(pl.sensors, truth_p, model)
        s_o_p = score_on_truth(oracle.sensors, truth_p, model)
        s_r = score_on_lines(pl.sensors, ta, tp, model)
        row: dict[str, Any] = {
            "experiment": cfg.name,
            "scenario": cfg.scenario,
            **{f"param_{k}": v for k, v in setting.items()},
            "setting_id": setting_id,
            "horizon": horizon,
            "seed": seed,
            "strategy": strat,
            "detection_rate": s_e.detection_rate,
            "missed": s_e.missed,
            "total": s_e.total,
            "void_probability": s_e.void_probability,
            "oracle_detection_rate": oracle_e.detection_rate,
            "gap_pp": 100 * (oracle_e.detection_rate - s_e.detection_rate),
            "regret_plan": s_p.missed - s_o_p.missed,
            "realized_detection_rate": s_r.detection_rate,
            "n_test_lines": len(ta),
            "time_s": elapsed,
            "sensors": json.dumps(np.round(pl.sensors, 4).tolist()),
        }
        if f is not None:
            row["weight_fit"] = f.meta.get("weight_fit", "not_applicable")
            row["weight_fit_message"] = f.meta.get("weight_fit_message", "")
            mean_f = IntensityField(gp, f.density)
            pm = Problem(mean_f, model)
            row["l1_plan"] = f.l1(truth_p)
            row["delta_plan"] = float(pm.lambda_miss(pl.sensors)) - float(pm.lambda_miss(oracle.sensors))
            # coverage-weighted error: only intensity error where either
            # network detects something can cost detections (Prop. 1b)
            cover = np.maximum(1 - pm.miss(pl.sensors), 1 - pm.miss(oracle.sensors))
            err = np.abs(f.mass - truth_p.mass)[gp.mask]
            row["l1_cov_plan"] = float(err @ cover)
            if f.samples is not None:
                sample_losses = np.asarray(plan_prob.lambda_miss(pl.sensors, per_sample=True))
                row.update(sample_diagnostics(sample_losses, s_p.missed))
                row["sample_mean_relative_l1"] = float(
                    np.abs(f.sample_mass.mean(axis=0) - f.mass).sum() / max(f.total(), 1e-12)
                )
            if "weights" in f.meta and isinstance(f.meta["weights"], dict):
                row["weights"] = json.dumps({k: round(float(v), 4) for k, v in f.meta["weights"].items()})
        if cfg.vary_scenario_seed:
            row["sensors_full"] = json.dumps(pl.sensors.tolist())
        rows.append(row)
    return rows


def sample_diagnostics(losses: FloatArray, truth: float) -> dict[str, float | int | bool]:
    """Empirical rank/coverage of latent expected loss, not a Poisson-count PIT."""
    values = np.asarray(losses, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all() or not np.isfinite(truth):
        raise ValueError("finite nonempty sample losses and truth required")
    low, high = np.quantile(values, [0.05, 0.95], method="linear")
    return {
        "sample_rank": float((np.sum(values < truth) + 0.5 * np.sum(values == truth)) / len(values)),
        "sample_covered_90": bool(low <= truth <= high),
        "sample_low": float(low),
        "sample_high": float(high),
        "sample_true_loss": float(truth),
        "sample_count": len(values),
    }


def _worker(args: tuple[dict[str, Any], dict[str, Any], int, int, int]) -> list[dict[str, Any]]:
    cfgd, setting, sid, h, seed = args
    return run_replicate(ExperimentConfig(**cfgd), setting, sid, h, seed)


def run_experiment(
    cfg: ExperimentConfig, out_dir: str | Path, workers: int | None = None, progress: bool = True
) -> Path:
    """Run all replicates, write ``runs.csv``, ``summary.csv`` and ``meta.json``."""
    import pandas as pd

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [
        (cfg.to_dict(), setting, sid, h, cfg.seed_offset + s)
        for sid, setting in enumerate(cfg.settings())
        for h in cfg.horizons
        for s in range(cfg.seeds)
    ]
    workers = workers or max(1, min(4, os.cpu_count() or 2))
    if workers < 1:
        raise ValueError("workers must be positive")
    t0 = time.time()
    rows: list[dict[str, Any]] = []
    if workers == 1:
        it: Iterable[list[dict[str, Any]]] = map(_worker, jobs)
    else:
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        ex = ProcessPoolExecutor(max_workers=workers)
        it = ex.map(_worker, jobs, chunksize=max(1, len(jobs) // (8 * workers)))
    for i, r in enumerate(it, 1):
        rows.extend(r)
        if progress and (i % max(1, len(jobs) // 20) == 0 or i == len(jobs)):
            print(f"  [{cfg.name}] {i}/{len(jobs)} replicates  ({time.time() - t0:.0f}s)", flush=True)
    if workers != 1:
        ex.shutdown()
    df = pd.DataFrame(rows)
    df.to_csv(out / "runs.csv", index=False)
    summ = summarise(df)
    summ.to_csv(out / "summary.csv", index=False)
    cfg_text = json.dumps(cfg.to_dict(), sort_keys=True, default=str)
    meta = {
        "experiment": cfg.name,
        "stochplace_version": __version__,
        "git_commit": _git_commit(),
        "config_sha256": hashlib.sha256(cfg_text.encode()).hexdigest()[:16],
        "config": cfg.to_dict(),
        "n_replicates": len(jobs),
        "wall_time_s": round(time.time() - t0, 1),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "dependencies": _dependency_versions(),
        "source_sha256": _source_hash(),
        "validation": "rolling_origin_training_prefix_only",
        "platform": platform.platform(),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2, default=str))
    return out


def _dependency_versions() -> dict[str, str]:
    from importlib.metadata import version

    return {name: version(name) for name in ("numpy", "scipy", "pandas", "matplotlib", "pyyaml")}


def _source_hash() -> str:
    """Content fingerprint independent of rebases or output-only commits."""
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(root.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def summarise(df: Any, baseline: str = "pooled") -> Any:
    """Per-strategy means with bootstrap CIs and paired gains over ``baseline``."""
    import pandas as pd

    keys = [c for c in df.columns if c.startswith("param_")] + ["horizon"]
    out = []
    for gkey, g in df.groupby([*keys, "strategy"], sort=False):
        gkey = gkey if isinstance(gkey, tuple) else (gkey,)
        rec = dict(zip([*keys, "strategy"], gkey))
        for col in ("detection_rate", "gap_pp", "void_probability", "realized_detection_rate"):
            m, lo, hi = bootstrap_ci(g[col].to_numpy())
            rec[f"{col}_mean"] = m
            rec[f"{col}_lo"] = lo
            rec[f"{col}_hi"] = hi
        if "l1_plan" in g:
            rec["l1_plan_mean"] = float(g["l1_plan"].mean())
        rec["n"] = len(g)
        # paired comparison with baseline on the same seeds
        sel = df["strategy"] == baseline
        for k, v in zip(keys, gkey[:-1]):
            sel &= df[k] == v
        base = df[sel].set_index("seed")["detection_rate"]
        cur = g.set_index("seed")["detection_rate"]
        common = cur.index.intersection(base.index)
        if len(common) and rec["strategy"] != baseline:
            diff = 100 * (cur.loc[common] - base.loc[common]).to_numpy()
            m, lo, hi = bootstrap_ci(diff)
            rec["gain_vs_baseline_pp"] = m
            rec["gain_vs_baseline_lo"] = lo
            rec["gain_vs_baseline_hi"] = hi
            rec["win_rate_vs_baseline"] = float(np.mean(diff > 0))
        out.append(rec)
    return pd.DataFrame(out)
