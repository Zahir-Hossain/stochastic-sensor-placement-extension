"""Publication figures built from ``results/``.

Colour follows the strategy, never its rank, and is the same in every
figure. Robust variants (``:cvar``, ``:void``) reuse the base hue with a
dashed line or hollow marker so identity never rests on colour alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8984"
GRIDC = "#e6e5e0"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

#: fixed categorical slots (validated default palette, light mode)
COLORS = {
    "stacked": "#2a78d6",
    "pseudo_bma": "#9969a7",
    "pooled": "#eb6834",
    "drift_u": "#1baf7a",
    "trend": "#eda100",
    "recent": "#e87ba4",
    "drift": "#008300",
    "mixture": "#6250d6",
    "lgcp": "#e34948",
    "oracle": INK,
    "hindsight": INK,
    "fence": MUTED,
    "random": "#b5b4ae",
}

LABELS = {
    "pooled": "historical (pooled KDE)",
    "lgcp": "historical (LGCP)",
    "recent": "recent epochs",
    "drift": "drift forecast",
    "drift_u": "drift + uncertainty",
    "trend": "log-linear trend",
    "mixture": "$\\lambda_E$, fixed weights (v0.1 idea)",
    "stacked": "intensity stacking",
    "pseudo_bma": "pseudo-BMA",
    "oracle": "oracle (true future)",
    "hindsight": "hindsight (test epoch)",
    "fence": "evenly spaced fence",
    "random": "random",
}


def _style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.edgecolor": MUTED,
            "axes.labelcolor": INK2,
            "axes.titlecolor": INK,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.labelsize": 9.5,
            "xtick.color": INK2,
            "ytick.color": INK2,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRIDC,
            "grid.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "legend.fontsize": 8.5,
            "font.family": "DejaVu Sans",
            "lines.linewidth": 2.0,
            "lines.markersize": 6,
        }
    )


def _base(strategy: str) -> tuple[str, str]:
    src, _, obj = strategy.partition(":")
    return src, obj


def color(strategy: str) -> str:
    return COLORS.get(_base(strategy)[0], INK2)


def label(strategy: str) -> str:
    src, obj = _base(strategy)
    lab = LABELS.get(src, src)
    names = {"void": "expected void obj.", "cvar": "CVaR obj."}
    return f"{lab}, {names.get(obj, obj)}" if obj else lab


def _save(fig: plt.Figure, out: Path, name: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / f"{name}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


# ----------------------------------------------------------------------
def fig_representation(out: Path) -> None:
    """Lines <-> points, and a sensor's coverage band in (alpha, p)."""
    from .geometry import Window, lines_to_rep

    _style()
    rng = np.random.default_rng(4)
    w = Window(-10, 10, -5, 5)
    m = rng.normal(0.15, 0.25, 9)
    b = rng.normal(0.0, 2.2, 9)
    a, p = lines_to_rep(m, b)
    sx, sy, r = 3.0, 1.0, 1.0
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.25, 1]})
    x = np.linspace(-10, 10, 50)
    d = np.abs(sx * np.cos(a) + sy * np.sin(a) - p)
    near = d <= 2 * r
    for i in range(len(m)):
        ax[0].plot(x, m[i] * x + b[i], color=SEQ[4] if near[i] else MUTED, lw=1.6 if near[i] else 1.0)
    ax[0].add_patch(
        Rectangle((w.xmin, w.ymin), w.xmax - w.xmin, w.ymax - w.ymin, fill=False, ec=INK2, lw=1, ls="--")
    )
    ax[0].add_patch(plt.Circle((sx, sy), 2 * r, color=SEQ[0], alpha=0.6, lw=0))
    ax[0].plot(sx, sy, "o", color=INK, ms=7)
    ax[0].annotate(
        "sensor $(x_s, y_s)$",
        (sx, sy),
        (sx + 0.6, sy + 2.6),
        color=INK,
        fontsize=9,
        arrowprops={"arrowstyle": "-", "color": INK2, "lw": 0.8},
    )
    ax[0].set(
        xlim=(-11, 11), ylim=(-7, 7), xlabel="x", ylabel="y", title="Physical space: trajectories are lines"
    )
    ax[0].set_aspect("equal")
    aa = np.linspace(0, np.pi, 300)
    band = sx * np.cos(aa) + sy * np.sin(aa)
    ax[1].fill_between(aa, band - 2 * r, band + 2 * r, color=SEQ[0], alpha=0.7, lw=0)
    ax[1].plot(aa, band, color=SEQ[4], lw=1.5)
    ax[1].scatter(a[~near], p[~near], s=36, color=MUTED, zorder=3, edgecolor=SURFACE, lw=1.5)
    ax[1].scatter(a[near], p[near], s=46, color=SEQ[4], zorder=3, edgecolor=SURFACE, lw=1.5)
    ax[1].text(0.15, band[30] + 2.4, "$p = x_s\\cos\\alpha + y_s\\sin\\alpha$", color=INK, fontsize=9.5)
    ax[1].set(
        xlim=(0, np.pi),
        ylim=(-8, 8),
        xlabel="$\\alpha$ (rad)",
        ylabel="$p$",
        title="Representation space: lines are points",
    )
    ax[1].set_xticks([0, np.pi / 4, np.pi / 2, 3 * np.pi / 4, np.pi], ["0", "π/4", "π/2", "3π/4", "π"])
    fig.text(
        0.5,
        -0.04,
        "A sensor at $(x_s, y_s)$ covers the sinusoidal band $|x_s\\cos\\alpha + y_s\\sin\\alpha - p| \\lesssim 2r$. "
        "Lines inside the band (blue) pass within $2r$ of the sensor.",
        ha="center",
        color=INK2,
        fontsize=9,
    )
    _save(fig, out, "representation_space")


def fig_hero(out: Path, seed: int = 3, speed: float = 0.3) -> dict[str, float]:
    """One drifting-lane replicate: where each planner puts its sensors."""
    from .evaluate import score_on_lines
    from .forecast import ForecastConfig, _bandwidth, forecast
    from .grid import RepGrid
    from .objective import Problem
    from .optimize import solve
    from .scenarios import make_scenario
    from .sensors import GaussianSensor

    _style()
    sc = make_scenario("drift", speed=speed)
    w = sc.window
    rng = np.random.default_rng(seed)
    T, h = 8, 2
    hist = sc.history(T, rng)
    ta, tp = sc.sample(T - 1 + h, rng)
    g = RepGrid(w, 120, 64)
    model = GaussianSensor(0.95, 1.0)
    cand = w.grid(1.0)
    fcfg = ForecastConfig()
    bw = _bandwidth(hist, fcfg)
    fields = {
        "pooled": forecast(hist, g, h, "pooled", fcfg, bw),
        "stacked": forecast(hist, g, h, "stacked", fcfg, bw),
        "oracle": sc.truth(g, T - 1 + h),
    }
    sens = {k: solve(Problem(f, model), cand, 4, w).sensors for k, f in fields.items()}
    rates = {k: score_on_lines(s, ta, tp, model).detection_rate for k, s in sens.items()}

    fig = plt.figure(figsize=(12.5, 8.2))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.35, 1], hspace=0.75, wspace=0.28)
    ax = fig.add_subplot(gs[0, :2])
    x = np.linspace(-11, 11, 2)
    from .geometry import rep_to_lines

    ha = np.concatenate([e[0] for e in hist])
    hp = np.concatenate([e[1] for e in hist])
    sel = rng.choice(len(ha), size=min(160, len(ha)), replace=False)
    m, b = rep_to_lines(ha[sel], hp[sel])
    for mi, bi in zip(m, b):
        ax.plot(x, mi * x + bi, color=MUTED, lw=0.5, alpha=0.35)
    m2, b2 = rep_to_lines(ta, tp)
    for mi, bi in zip(m2, b2):
        ax.plot(x, mi * x + bi, color=SEQ[2], lw=0.7, alpha=0.55)
    ax.add_patch(
        Rectangle((w.xmin, w.ymin), w.xmax - w.xmin, w.ymax - w.ymin, fill=False, ec=INK2, lw=1, ls="--")
    )
    mk = {"pooled": ("s", 9), "stacked": ("o", 9), "oracle": ("x", 8)}
    for k, s in sens.items():
        shape, size = mk[k]
        kw: dict[str, Any] = (
            {"mec": color(k), "mfc": SURFACE, "mew": 2} if shape != "x" else {"color": color(k), "mew": 2}
        )
        ax.plot(
            s[:, 0],
            s[:, 1],
            shape,
            ms=size,
            ls="none",
            label=f"{label(k)}: {100 * rates[k]:.1f}% detected",
            **kw,
        )
    ax.plot([], [], color=MUTED, lw=1, label="history (8 epochs, sample)")
    ax.plot([], [], color=SEQ[2], lw=1, label="realised future (2 epochs ahead)")
    ax.set(xlim=(-11, 11), ylim=(-6, 6), xlabel="x", ylabel="y")
    ax.set_title("Traffic drifts; historical sensors watch where it used to be", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, fontsize=8)
    ax.set_aspect("equal")

    axb = fig.add_subplot(gs[0, 2])
    ks = ["pooled", "stacked", "oracle"]
    vals = [100 * (1 - rates[k]) for k in ks]
    axb.barh(range(3), vals, color=[color(k) for k in ks], height=0.55)
    for i, v in enumerate(vals):
        axb.text(v + 0.2, i, f"{v:.1f}%", va="center", color=INK, fontsize=9)
    axb.set_yticks(range(3), ["historical", "stacked $\\lambda_E$", "oracle"])
    axb.invert_yaxis()
    axb.set(xlabel="future trajectories missed (%)", xlim=(0, max(vals) * 1.3))
    axb.set_title("Missed in the realised future", loc="left")
    axb.grid(axis="y", visible=False)

    titles = {
        "pooled": "Historical intensity",
        "stacked": "Forecast intensity (stacked)",
        "oracle": "True future intensity",
    }
    vmax = max(float(f.density.max()) for f in fields.values())
    for i, k in enumerate(ks):
        a2 = fig.add_subplot(gs[1, i])
        f = fields[k]
        a2.imshow(
            f.density.T,
            origin="lower",
            aspect="auto",
            extent=(0, np.pi, -float(g.p_max or 0), float(g.p_max or 0)),
            cmap=matplotlib.colors.LinearSegmentedColormap.from_list("seq", [SURFACE, *SEQ]),
            vmin=0,
            vmax=vmax,
        )
        a2.set(xlim=(1.45, 2.3), ylim=(-6, 8), xlabel="$\\alpha$", ylabel="$p$" if i == 0 else "")
        a2.set_title(titles[k], loc="left", fontsize=10)
        a2.grid(False)
    _save(fig, out, "hero")
    return rates


def _ci_line(ax: plt.Axes, x: np.ndarray, d: pd.DataFrame, strat: str, ycol: str = "gap_pp") -> None:
    obj = _base(strat)[1]
    ls = {"void": "--", "cvar": ":"}.get(obj, "-")
    mk = {"void": "o", "cvar": "s"}.get(obj, "o")
    c = color(strat)
    kw: dict[str, Any] = {"mfc": SURFACE, "mew": 1.8} if obj else {}
    ls_: Any = ls
    if strat == "drift_u":  # coincides with stacked under pure drift: draw on top, dotted
        ls_, kw = (0, (1.5, 2.5)), {"zorder": 5}
    ax.plot(x, d[f"{ycol}_mean"], ls=ls_, color=c, marker=mk, ms=5, label=label(strat), **kw)
    ax.fill_between(x, d[f"{ycol}_lo"], d[f"{ycol}_hi"], color=c, alpha=0.12, lw=0)


def fig_drift_sweep(res: Path, out: Path) -> None:
    _style()
    s = pd.read_csv(res / "drift_sweep" / "summary.csv")
    strategies = ["pooled", "recent", "trend", "mixture", "drift_u", "stacked"]
    horizons = sorted(s.horizon.unique())
    fig, axes = plt.subplots(1, len(horizons), figsize=(11, 4.2), sharey=True)
    for ax, h in zip(np.atleast_1d(axes), horizons):
        for st in strategies:
            d = s[(s.strategy == st) & (s.horizon == h)].sort_values("param_speed")
            _ci_line(ax, d.param_speed.to_numpy(), d, st)
        ax.set(xlabel="lane drift speed (offset units per epoch)", title=f"Forecast horizon h = {h}")
        ax.axhline(0, color=INK, lw=1)
    np.atleast_1d(axes)[0].set_ylabel("detection gap to oracle (pp, lower is better)")
    np.atleast_1d(axes)[-1].legend(loc="upper left")
    fig.text(
        0.07,
        -0.03,
        "Drift + uncertainty (dotted) lies on top of stacked: under pure drift, stacking puts all weight on it.",
        fontsize=8.5,
        color=INK2,
    )
    fig.suptitle(
        "Planning on a forecast keeps up as drift grows; planning on history falls behind",
        x=0.07,
        ha="left",
        fontsize=12,
        fontweight="bold",
        color=INK,
    )
    _save(fig, out, "drift_sweep")


def fig_suite(res: Path, out: Path) -> None:
    _style()
    names = [
        ("suite_stationary", "Stationary"),
        ("suite_drift", "Drifting lane"),
        ("suite_lane_shift", "Traffic moves between lanes"),
        ("suite_emergence", "New lane emerges"),
    ]
    order = [
        "pooled",
        "lgcp",
        "recent",
        "drift",
        "drift_u",
        "drift_u:void",
        "drift_u:cvar",
        "trend",
        "trend:cvar",
        "mixture",
        "stacked",
        "stacked:void",
        "stacked:cvar",
        "fence",
    ]
    fig, axes = plt.subplots(1, 4, figsize=(14, 5.6), sharey=True)
    for ax, (n, title) in zip(axes, names):
        p = res / n / "summary.csv"
        if not p.exists():
            ax.set_visible(False)
            continue
        s = pd.read_csv(p).set_index("strategy")
        for i, st in enumerate(order):
            if st not in s.index:
                continue
            r = s.loc[st]
            hollow = ":" in st
            ax.errorbar(
                r.gap_pp_mean,
                i,
                xerr=[[r.gap_pp_mean - r.gap_pp_lo], [r.gap_pp_hi - r.gap_pp_mean]],
                fmt="o",
                color=color(st),
                mfc=SURFACE if hollow else color(st),
                mew=2,
                ms=7,
                capsize=0,
                lw=2,
            )
        ax.set_xscale("symlog", linthresh=1.0)
        ax.set_xlim(-0.05, 40)
        ax.set_title(title, loc="left")
        ax.set_xlabel("gap to oracle (pp, log scale)")
        ax.axvline(0, color=INK, lw=1)
        ax.grid(axis="y", visible=False)
    first = next(a for a in axes if a.get_visible())
    first.set_yticks(range(len(order)), [label(o) for o in order])
    first.invert_yaxis()
    fig.suptitle(
        "Detection gap to the oracle, 40 seeds, 95% bootstrap CI (random placement omitted: 28 to 42 pp)",
        x=0.01,
        ha="left",
        fontsize=11.5,
        fontweight="bold",
        color=INK,
    )
    _save(fig, out, "scenario_suite")


def fig_bound(res: Path, out: Path) -> dict[str, float]:
    _style()
    frames = []
    for p in res.glob("*/runs.csv"):
        d = pd.read_csv(p)
        if "l1_plan" in d:
            frames.append(d.dropna(subset=["l1_plan"]))
    d = pd.concat(frames)
    d = d[d.strategy != "oracle"]
    tot = d.total
    rel_reg = d.regret_plan / tot
    dpos = d.delta_plan.clip(lower=0)
    stats: dict[str, float] = {"runs": float(len(d))}
    floor = 1e-5
    cols = [
        (
            "l1_plan",
            "Proposition 1a: plain $L_1$ error",
            "$\\|\\lambda-\\hat\\lambda\\|_1$ / expected traffic",
        )
    ]
    if "l1_cov_plan" in d:
        cols.append(
            (
                "l1_cov_plan",
                "Proposition 1b: coverage-weighted error",
                "$\\int |\\lambda-\\hat\\lambda|\\,\\max(1-q_{\\hat S}, 1-q_{S^*})$ / expected traffic",
            )
        )
    fig, axes = plt.subplots(1, len(cols), figsize=(6.0 * len(cols), 4.8), squeeze=False)
    for ax, (col, title, xl) in zip(axes[0], cols):
        x = d[col] / tot
        holds = float(np.mean(d.regret_plan <= dpos + d[col] + 1e-9))
        rho = float(pd.Series(x.to_numpy()).corr(pd.Series(rel_reg.to_numpy()), method="spearman"))
        stats[f"{col}_bound_holds"] = holds
        stats[f"{col}_spearman"] = rho
        stats[f"{col}_median_ratio"] = float(np.median(rel_reg[rel_reg > 0] / x[rel_reg > 0]))
        ax.scatter(x, np.maximum(rel_reg, floor), s=6, color=SEQ[4], alpha=0.25, lw=0)
        xx = np.logspace(-6, 1, 50)
        ax.plot(xx, xx, color=INK, lw=1.5, label="regret = error (the bound)")
        ax.set(
            xscale="log",
            yscale="log",
            ylim=(floor * 0.8, 3),
            xlabel=xl,
            ylabel="regret vs oracle / expected traffic",
        )
        ax.set_xlim(max(floor * 0.8, float(x[x > 0].min()) * 0.5), 3)
        ax.set_title(title, loc="left")
        ax.legend(loc="upper left")
        ax.text(
            0.98,
            0.03,
            f"bound holds in {100 * holds:.1f}% of {len(d):,} runs\nSpearman rank corr. {rho:.2f}",
            transform=ax.transAxes,
            ha="right",
            fontsize=8,
            color=INK2,
        )
    _save(fig, out, "regret_bound")
    return stats


def fig_scarcity(res: Path, out: Path) -> None:
    p = res / "data_scarcity" / "summary.csv"
    if not p.exists():
        return
    _style()
    s = pd.read_csv(p)
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    for st in ["pooled", "lgcp", "lgcp:void", "lgcp:cvar"]:
        d = s[s.strategy == st].sort_values("param_rate")
        _ci_line(ax, 4 * d.param_rate.to_numpy(), d, st)
    ax.set(xscale="log", xlabel="trajectories observed (4 epochs)", ylabel="detection gap to oracle (pp)")
    ax.set_title("Little data, stationary traffic", loc="left")
    ax.axhline(0, color=INK, lw=1)
    ax.legend()
    _save(fig, out, "data_scarcity")


def fig_approximation(res: Path, out: Path) -> None:
    p = res / "approximation" / "runs.csv"
    if not p.exists():
        return
    _style()
    d = pd.read_csv(p)
    fig, ax = plt.subplots(figsize=(6.2, 4))
    ax.hist(d.ratio, bins=np.linspace(min(0.9, d.ratio.min()), 1.0, 26).tolist(), color=SEQ[4], rwidth=0.9)
    ax.axvline(1 - 1 / np.e, color=INK, lw=1.5)
    ax.text(1 - 1 / np.e + 0.002, ax.get_ylim()[1] * 0.9, "guarantee 1 - 1/e", fontsize=8.5, color=INK)
    ax.set(xlabel="greedy detected mass / exact optimum", ylabel="instances", xlim=(0.6, 1.005))
    ax.set_title(f"Greedy vs exhaustive search ({len(d)} instances, k = 3)", loc="left")
    _save(fig, out, "greedy_vs_optimum")


def fig_legacy(out: Path) -> dict[str, object]:
    """v0.1 scoring vs scoring every placement on the same future routes."""
    from .legacy import legacy_pipeline, legacy_routes

    _style()
    s, b = legacy_routes(np.random.default_rng(1))
    r = legacy_pipeline(s, b)
    fs, fb = r.routes["prediction"]

    def miss_on(
        sensors: np.ndarray, sl: np.ndarray, ic: np.ndarray, rho: float = 0.95, rr: float = 1.5
    ) -> float:
        q = np.ones(len(sl))
        for x, y in sensors:
            d = np.abs(sl * x - y + ic) / np.sqrt(sl**2 + 1)
            q *= 1 - rho * np.exp(-(d**2) / (2 * rr**2))
        return float(q.mean())

    own = r.normalized_miss
    cross = {
        "historical": miss_on(r.historical_sensors, fs, fb),
        "prediction": miss_on(r.future_sensors, fs, fb),
        "uncertainty": miss_on(r.uncertainty_sensors, fs, fb),
    }
    # the same v0.1 pipeline with a binding budget (2 sensors, r = 0.5)
    from .legacy import legacy_candidates, legacy_greedy

    cand = legacy_candidates()
    tight = {}
    for nm, (sl, ic) in r.routes.items():
        sens, _ = legacy_greedy(sl, ic, cand, k=2, r=0.5)
        tight[nm] = miss_on(sens, fs, fb, rr=0.5)
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.9))
    keys = ["historical", "prediction", "uncertainty"]
    cols = [COLORS["pooled"], COLORS["drift"], COLORS["drift_u"]]
    for a_, data, title in [
        (ax[0], own, "v0.1 as reported:\neach placement scored on its own routes"),
        (ax[1], cross, "Same placements,\nall scored on the future routes"),
        (ax[2], tight, "Binding budget (2 sensors, r = 0.5),\nall scored on the future routes"),
    ]:
        v = [100 * data[k] for k in keys]
        a_.bar(range(3), v, color=cols, width=0.6)
        for i, vi in enumerate(v):
            a_.text(
                i,
                vi,
                f"{vi:.3f}%" if vi < 1 else f"{vi:.1f}%",
                ha="center",
                va="bottom",
                fontsize=8.5,
                color=INK,
            )
        a_.set_xticks(range(3), keys)
        a_.set_title(title, loc="left", fontsize=9.5)
        a_.grid(axis="x", visible=False)
        a_.set_ylim(0, max(v) * 1.25)
    ax[0].set_ylabel("trajectories missed (%)")
    _save(fig, out, "legacy_v01_check")
    return {"own_routes": own, "on_future_routes": cross, "binding_budget_on_future": tight}


def fig_ais(res: Path, out: Path) -> None:
    d = res / "ais_gothenburg"
    if not (d / "summary.csv").exists():
        return
    from .ais import GOTHENBURG_WINDOW as W

    _style()
    lines = pd.read_csv(d / "lines.csv")
    runs = pd.read_csv(d / "runs.csv")
    summ = pd.read_csv(d / "summary.csv")
    fig, ax = plt.subplots(1, 2, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1.45, 1], "wspace": 0.62})
    for _, r in lines.iterrows():
        ax[0].plot([r.x0, r.x1], [r.y0, r.y1], color=SEQ[3], lw=0.9, alpha=0.6)
    ax[0].add_patch(
        Rectangle((W.xmin, W.ymin), W.xmax - W.xmin, W.ymax - W.ymin, fill=False, ec=INK2, ls="--", lw=1)
    )
    last = runs.origin.max()
    for st, mk in [("stacked", "o"), ("fence", "s")]:
        row = runs[(runs.strategy == st) & (runs.origin == last)]
        if len(row) and isinstance(row.iloc[0].get("sensors"), str):
            s = np.array(json.loads(row.iloc[0].sensors))
            ax[0].plot(
                s[:, 0],
                s[:, 1],
                mk,
                ms=9,
                mfc=SURFACE,
                mec=color(st),
                mew=2,
                ls="none",
                label=f"{label(st)} (last origin)",
            )
    ax[0].set(
        xlabel="east (km)",
        ylabel="north (km)",
        xlim=(W.xmin - 0.3, W.xmax + 0.3),
        ylim=(W.ymin - 0.3, W.ymax + 0.3),
    )
    ax[0].set_aspect("equal")
    ax[0].set_title(f"{len(lines)} straight passage pieces, Gothenburg, 5 July 2017", loc="left")
    ax[0].legend(loc="lower right")
    order = [
        "random",
        "fence",
        "trend",
        "drift_u",
        "recent",
        "lgcp",
        "mixture",
        "stacked:cvar",
        "stacked:void",
        "stacked",
        "pooled",
        "hindsight",
    ]
    stats = {
        str(k): (m, lo_, hi_)
        for k, m, lo_, hi_ in zip(
            summ["strategy"],
            summ["mean_over_origins"].to_numpy(float),
            summ["lo"].to_numpy(float),
            summ["hi"].to_numpy(float),
        )
    }
    order = [o for o in order if o in stats]
    for i, st in enumerate(order):
        mean, lo, hi = stats[st]
        hollow = ":" in st
        ax[1].errorbar(
            100 * mean,
            i,
            xerr=[[100 * (mean - lo)], [100 * (hi - mean)]],
            fmt="o",
            color=color(st),
            mfc=SURFACE if hollow else color(st),
            mew=2,
            ms=7,
            lw=2,
        )
    ax[1].set_yticks(range(len(order)), [label(o) for o in order])
    ax[1].set(xlabel="detection rate on the next 3-hour epoch (%)")
    ax[1].set_title(f"Rolling-origin test, {int(summ['n_origins'].to_numpy().max())} origins", loc="left")
    ax[1].grid(axis="y", visible=False)
    _save(fig, out, "ais_case_study")


def make_all(results: Path, out: Path) -> dict[str, object]:
    stats: dict[str, object] = {}
    fig_representation(out)
    stats["hero_rates"] = fig_hero(out)
    stats["legacy"] = fig_legacy(out)
    if (results / "drift_sweep" / "summary.csv").exists():
        fig_drift_sweep(results, out)
    fig_suite(results, out)
    stats["bound"] = fig_bound(results, out)
    fig_scarcity(results, out)
    fig_approximation(results, out)
    fig_ais(results, out)
    (results / "figure_stats.json").write_text(json.dumps(stats, indent=2, default=float))
    return stats
