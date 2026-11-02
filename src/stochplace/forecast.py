"""Forecasting future trajectory intensity from a history of epochs.

Every forecaster maps a history ``[(alpha_t, p_t) for t in 0..T-1]`` and
a target time ``t* = T - 1 + h`` to an :class:`~stochplace.grid.IntensityField`
whose ``density`` is the predictive mean and whose ``samples`` (when
present) are draws from the predictive distribution.

Forecasters
-----------
``pooled``     all history pooled (the historical-only baseline)
``recent``     last ``L`` epochs only (persistence)
``drift``      advection: shift each line by the fitted centroid velocity
``drift_u``    ``drift`` + predictive uncertainty of the velocity folded
               into the kernel (the "uncertainty-expanded" intensity)
``trend``      per-cell log-linear trend with residual-bootstrap samples
``mixture``    the original fixed-weight ``lambda_E`` proposal
``pseudo_bma`` softmax of rolling-origin individual model log scores
``stacked``    simplex weights maximising the held-out Poisson log score
               of the combined intensity (intensity stacking)
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from ._typing import FloatArray
from .geometry import canonicalize
from .grid import IntensityField, RepGrid
from .intensity import _cell_mass_matrix, _with_images, cv_bandwidth, kde_intensity

History = Sequence[tuple[FloatArray, FloatArray]]

__all__ = [
    "FORECASTERS",
    "ForecastConfig",
    "backtest_log_scores",
    "forecast",
    "poisson_log_score",
]


@dataclass(frozen=True)
class ForecastConfig:
    """Shared settings for all forecasters.

    Attributes
    ----------
    bandwidth
        Fixed kernel bandwidth ``(h_alpha, h_p)``. When ``None`` it is
        chosen by likelihood CV on the most recent ``recent`` epochs and
        shared by every model, so models differ only in how they use time.
    recent
        Window length for ``recent`` and for bandwidth selection.
    n_samples
        Predictive samples drawn by stochastic forecasters.
    max_log_change
        Clip on the per-cell log-intensity change for ``trend``.
    mixture_weights
        ``(w_H, w_F, w_U)`` for ``mixture``.
    stack_models, backtest_epochs
        Candidate models and number of rolling origins for ``stacked``.
    """

    bandwidth: tuple[float, float] | None = None
    recent: int = 2
    n_samples: int = 32
    max_log_change: float = 2.0
    mixture_weights: tuple[float, float, float] = (1 / 3, 1 / 3, 1 / 3)
    stack_models: tuple[str, ...] = ("pooled", "recent", "drift_u", "trend")
    backtest_epochs: int = 3

    def __post_init__(self) -> None:
        if self.recent < 1 or self.n_samples < 1 or self.backtest_epochs < 1:
            raise ValueError("recent, n_samples and backtest_epochs must be positive")
        if self.max_log_change <= 0 or not np.isfinite(self.max_log_change):
            raise ValueError("max_log_change must be finite and positive")
        if self.bandwidth is not None and (
            len(self.bandwidth) != 2 or not np.all(np.isfinite(self.bandwidth)) or min(self.bandwidth) <= 0
        ):
            raise ValueError("bandwidth needs two finite positive values")
        allowed = {"pooled", "recent", "drift", "drift_u", "trend"}
        if not self.stack_models or not set(self.stack_models) <= allowed:
            raise ValueError("stack_models must contain base forecasters only")
        if len(set(self.stack_models)) != len(self.stack_models):
            raise ValueError("stack_models must be distinct")


def _concat(history: History, epochs: Sequence[int]) -> tuple[FloatArray, FloatArray, FloatArray]:
    a = [np.asarray(history[t][0]) for t in epochs]
    p = [np.asarray(history[t][1]) for t in epochs]
    tt = [np.full(len(x), float(t)) for t, x in zip(epochs, a)]
    if not a:
        return np.empty(0), np.empty(0), np.empty(0)
    return np.concatenate(a), np.concatenate(p), np.concatenate(tt)


def _bandwidth(history: History, cfg: ForecastConfig) -> tuple[float, float]:
    if cfg.bandwidth is not None:
        return cfg.bandwidth
    T = len(history)
    a, p, _ = _concat(history, range(max(0, T - cfg.recent), T))
    if len(a) < 5:
        a, p, _ = _concat(history, range(T))
    if len(a) < 2:
        return (0.05, 0.25)
    return cv_bandwidth(a, p)


# ----------------------------------------------------------------------
def _pooled(
    history: History, grid: RepGrid, t_star: float, cfg: ForecastConfig, bw: tuple[float, float]
) -> IntensityField:
    T = len(history)
    a, p, _ = _concat(history, range(T))
    return kde_intensity(a, p, grid, bandwidth=bw, n_epochs=T, label="pooled")


def _recent(
    history: History, grid: RepGrid, t_star: float, cfg: ForecastConfig, bw: tuple[float, float]
) -> IntensityField:
    T = len(history)
    L = min(cfg.recent, T)
    a, p, _ = _concat(history, range(T - L, T))
    return kde_intensity(a, p, grid, bandwidth=bw, n_epochs=L, label="recent")


@dataclass
class _DriftFit:
    v: FloatArray  # velocity (alpha, p) per epoch
    v_var: FloatArray  # sampling variance of velocity estimate
    res_var: FloatArray  # residual (process) variance of centroids
    count_rate: float
    t_mean: float
    s_tt: float


def _lift_history(history: History) -> list[tuple[FloatArray, FloatArray]]:
    """Lift local lane headings continuously across the Moebius seam.

    Each epoch uses a doubled-angle circular mean, unwrapped towards the
    preceding epoch. Offsets flip whenever a normal is rotated by pi.
    This is a local-lane model; widely separated headings remain a model
    misspecification, not a reason to average raw canonical angles.
    """
    lifted = []
    previous: float | None = None
    for a, p in history:
        if len(a) == 0:
            lifted.append((np.asarray(a), np.asarray(p)))
            continue
        heading = float(0.5 * np.angle(np.mean(np.exp(2j * np.asarray(a)))))
        if previous is None:
            heading += np.pi * np.rint((float(a[0]) - heading) / np.pi)
        else:
            heading += np.pi * np.rint((previous - heading) / np.pi)
        turns = np.rint((heading - np.asarray(a)) / np.pi).astype(int)
        aa = np.asarray(a) + turns * np.pi
        pp = np.asarray(p) * np.where(turns % 2 == 0, 1.0, -1.0)
        lifted.append((aa, pp))
        previous = float(np.mean(aa))
    return lifted


def _fit_drift(history: History) -> _DriftFit:
    T = len(history)
    ts, cents, ns = [], [], []
    for t, (a, p) in enumerate(_lift_history(history)):
        if len(a) == 0:
            continue
        ts.append(float(t))
        cents.append([float(np.mean(a)), float(np.mean(p))])
        ns.append(len(a))
    t_arr = np.array(ts)
    c = np.array(cents)
    n = np.array(ns, dtype=float)
    rate = float(n.mean()) if len(n) else 0.0
    if len(t_arr) < 3:
        return _DriftFit(np.zeros(2), np.zeros(2), np.zeros(2), rate, float(T - 1), 1.0)
    w = n / n.sum()
    tm = float(w @ t_arr)
    s_tt = float(w @ (t_arr - tm) ** 2)
    cm = w @ c
    v = ((w * (t_arr - tm)) @ (c - cm)) / s_tt
    resid = c - (cm + np.outer(t_arr - tm, v))
    dof = max(len(t_arr) - 2, 1)
    # unweighted residual variance per axis, then OLS variance of slope
    res_var = (resid**2).sum(axis=0) / dof
    v_var = res_var / (s_tt * len(t_arr))
    # sigma is estimated from few epochs: use the variance of the Student-t
    # predictive rather than the plug-in normal variance
    if dof > 2:
        v_var = v_var * dof / (dof - 2)
    return _DriftFit(v, v_var, res_var, rate, tm, s_tt)


def _drift_field(
    history: History,
    grid: RepGrid,
    t_star: float,
    bw: tuple[float, float],
    fit: _DriftFit,
    v: FloatArray,
    offset: FloatArray,
    extra_var: FloatArray | None,
) -> FloatArray:
    T = len(history)
    a, p, tt = _concat(_lift_history(history), range(T))
    lead = t_star - tt
    a2 = a + v[0] * lead + offset[0]
    p2 = p + v[1] * lead + offset[1]
    ha = np.full(len(a), bw[0])
    hp = np.full(len(a), bw[1])
    if extra_var is not None:
        ha = np.sqrt(ha**2 + extra_var[0] * lead**2 + fit.res_var[0])
        hp = np.sqrt(hp**2 + extra_var[1] * lead**2 + fit.res_var[1])
    a2, p2 = canonicalize(a2, p2)
    ai, pi_, wi = _with_images(a2, p2, np.ones(len(a)))
    hai = np.concatenate([ha, ha, ha])
    hpi = np.concatenate([hp, hp, hp])
    mass = _cell_mass_matrix(grid, ai, pi_, wi, hai, hpi)
    return mass / grid.cell_area / T


def _drift(
    history: History, grid: RepGrid, t_star: float, cfg: ForecastConfig, bw: tuple[float, float]
) -> IntensityField:
    fit = _fit_drift(history)
    dens = _drift_field(history, grid, t_star, bw, fit, fit.v, np.zeros(2), None)
    return IntensityField(grid, dens, label="drift", meta={"velocity": fit.v.tolist()})


def _drift_u(
    history: History,
    grid: RepGrid,
    t_star: float,
    cfg: ForecastConfig,
    bw: tuple[float, float],
    rng: np.random.Generator | None = None,
) -> IntensityField:
    """Drift forecast with predictive uncertainty.

    The mean field convolves each shifted kernel with the predictive
    distribution of its shift, ``N(0, Var(v) * lead^2 + sigma_res^2)``.
    Samples draw a velocity and an offset from that distribution.
    """
    rng = rng or np.random.default_rng(0)
    fit = _fit_drift(history)
    mean = _drift_field(history, grid, t_star, bw, fit, fit.v, np.zeros(2), fit.v_var)
    T = len(history)
    lead_bar = t_star - fit.t_mean
    samples = []
    for _ in range(cfg.n_samples):
        v = fit.v + np.sqrt(fit.v_var) * rng.standard_normal(2)
        off = np.sqrt(fit.res_var) * rng.standard_normal(2)
        samples.append(_drift_field(history, grid, t_star, bw, fit, v, off, None))
    return IntensityField(
        grid,
        mean,
        samples=np.stack(samples),
        label="drift_u",
        meta={
            "velocity": fit.v.tolist(),
            "velocity_sd": np.sqrt(fit.v_var).tolist(),
            "lead": lead_bar,
            "T": T,
        },
    )


def _trend(
    history: History,
    grid: RepGrid,
    t_star: float,
    cfg: ForecastConfig,
    bw: tuple[float, float],
    rng: np.random.Generator | None = None,
) -> IntensityField:
    """Per-cell log-linear trend fitted to per-epoch kernel estimates.

    Predictive samples come from a residual bootstrap (resample whole
    residual fields, refit, predict, add a residual), which keeps the
    spatial correlation of the errors.
    """
    rng = rng or np.random.default_rng(0)
    T = len(history)
    fields = np.stack([kde_intensity(a, p, grid, bandwidth=bw, label="epoch").density for a, p in history])
    if T < 3:
        f = fields.mean(axis=0)
        return IntensityField(grid, f, label="trend")
    floor = 1e-3 * max(float(fields.max()), 1e-12)
    y = np.log(fields + floor)
    t = np.arange(T, dtype=float)
    tm = t.mean()
    s_tt = float(((t - tm) ** 2).sum())

    def fit_predict(yy: FloatArray) -> tuple[FloatArray, FloatArray]:
        ym = yy.mean(axis=0)
        b = np.tensordot(t - tm, yy - ym, axes=(0, 0)) / s_tt
        last = ym + b * (T - 1 - tm)
        pred = ym + b * (t_star - tm)
        pred = np.clip(pred, last - cfg.max_log_change, last + cfg.max_log_change)
        fitted = ym[None] + b[None] * (t - tm)[:, None, None]
        return pred, fitted

    pred, fitted = fit_predict(y)
    resid = y - fitted
    # The trend models the *shape* of the intensity. The total is
    # forecast separately (mean epoch count), otherwise exponential
    # extrapolation at the leading edge of a moving lane inflates mass.
    target_total = float(np.mean([len(a) for a, _ in history]))

    def to_field(logf: FloatArray) -> FloatArray:
        f = np.where(grid.mask, np.maximum(np.exp(logf) - floor, 0.0), 0.0)
        tot = float(f.sum() * grid.cell_area)
        return f * (target_total / tot) if tot > 0 else f

    point = to_field(pred)
    samples = []
    for _ in range(cfg.n_samples):
        idx = rng.integers(0, T, T)
        y_b = fitted + resid[idx]
        pred_b, _ = fit_predict(y_b)
        eps = resid[rng.integers(0, T)]
        samples.append(to_field(pred_b + eps))
    s = np.stack(samples)
    # use the bootstrap mean so samples and density are consistent
    return IntensityField(
        grid,
        s.mean(axis=0),
        samples=s,
        label="trend",
        meta={"point_total": float(point.sum() * grid.cell_area)},
    )


def _mixture(
    history: History, grid: RepGrid, t_star: float, cfg: ForecastConfig, bw: tuple[float, float]
) -> IntensityField:
    """Original proposal: ``w_H lambda_H + w_F lambda_F + w_U lambda_U``."""
    h = _pooled(history, grid, t_star, cfg, bw)
    f = _drift(history, grid, t_star, cfg, bw)
    u = _drift_u(history, grid, t_star, cfg, bw)
    return IntensityField.mixture([h, f, u], list(cfg.mixture_weights), label="mixture")


# ----------------------------------------------------------------------
def poisson_log_score(field: IntensityField, alpha: FloatArray, p: FloatArray) -> float:
    """Poisson process log-likelihood ``sum_i log lambda(x_i) - integral lambda``.

    Lines outside the grid's p-range or mask are ignored. A small floor
    keeps the score finite where the forecast puts no mass.
    """
    g = field.grid
    ia, jp = g.locate(alpha, p)
    ok = jp >= 0
    dens = field.density
    vals = dens[ia[ok], jp[ok]]
    m = g.mask[ia[ok], jp[ok]]
    vals = vals[m]
    return float(np.sum(np.log(vals + 1e-12)) - field.total())


def _backtest_predictions(
    history: History,
    grid: RepGrid,
    horizon: int,
    models: Sequence[str],
    cfg: ForecastConfig,
    bw: tuple[float, float] | None = None,
) -> list[tuple[list[IntensityField], FloatArray, FloatArray]]:
    """Fit every preprocessing step using only the training prefix.

    ``bw`` is an explicitly predeclared fixed bandwidth for callers that
    need one. Ensemble forecasters deliberately do not pass the final-fit
    bandwidth: that fit has seen observations held out at earlier origins.
    """
    T = len(history)
    records = []
    for target in range(max(0, T - cfg.backtest_epochs), T):
        origin_len = target - horizon + 1
        if origin_len < 3:
            continue
        sub = history[:origin_len]
        train_bw = bw if bw is not None else _bandwidth(sub, cfg)
        fields = [FORECASTERS[m](sub, grid, float(target), cfg, train_bw) for m in models]
        a, p = history[target]
        records.append((fields, a, p))
    return records


def backtest_log_scores(
    history: History,
    grid: RepGrid,
    horizon: int,
    models: Sequence[str],
    cfg: ForecastConfig,
    bw: tuple[float, float] | None = None,
) -> dict[str, float]:
    """Sum of held-out log scores over rolling forecast origins."""
    scores = {m: 0.0 for m in models}
    for fields, a, p in _backtest_predictions(history, grid, horizon, models, cfg, bw):
        for m, f in zip(models, fields):
            scores[m] += poisson_log_score(f, a, p)
    return scores


def _pseudo_bma(
    history: History, grid: RepGrid, t_star: float, cfg: ForecastConfig, bw: tuple[float, float]
) -> IntensityField:
    """``lambda_E`` with weights from rolling-origin backtests.

    Weights are ``softmax(total held-out log score)`` (pseudo-BMA), so
    models that predicted recent epochs well get more weight.
    """
    T = len(history)
    horizon = max(1, round(t_star - (T - 1)))
    scores = backtest_log_scores(history, grid, horizon, cfg.stack_models, cfg)
    s = np.array([scores[m] for m in cfg.stack_models])
    w = np.exp(s - s.max())
    w = w / w.sum()
    return _combine_forecasts(history, grid, t_star, cfg, bw, w, "pseudo_bma", {"scores": scores})


def _combine_forecasts(
    history: History,
    grid: RepGrid,
    t_star: float,
    cfg: ForecastConfig,
    bw: tuple[float, float],
    w: FloatArray,
    label: str,
    meta: dict[str, object],
) -> IntensityField:
    fields = [FORECASTERS[m](history, grid, t_star, cfg, bw) for m in cfg.stack_models]
    out = IntensityField.mixture(fields, w.tolist(), label=label)
    # carry samples: pick each draw from a model chosen by weight
    rng = np.random.default_rng(1)
    picks = rng.choice(len(fields), size=cfg.n_samples, p=w)
    draws = []
    for j, mi in enumerate(picks):
        f = fields[mi]
        if f.samples is not None:
            draws.append(f.samples[j % len(f.samples)])
        else:
            draws.append(f.density)
    out.samples = np.stack(draws)
    out.meta = {"weights": dict(zip(cfg.stack_models, w.tolist())), **meta}
    return out


def _stacked(
    history: History, grid: RepGrid, t_star: float, cfg: ForecastConfig, bw: tuple[float, float]
) -> IntensityField:
    """Learn a convex intensity combination by held-out Poisson log score.

    This stacks Poisson *intensities*. A Poisson process at the combined
    intensity differs from a mixture of full point-process predictive
    distributions; no Bayesian posterior interpretation is asserted.
    """
    horizon = max(1, round(t_star - (len(history) - 1)))
    records = _backtest_predictions(history, grid, horizon, cfg.stack_models, cfg)
    n_models = len(cfg.stack_models)
    if not records:
        w = np.zeros(n_models)
        w[cfg.stack_models.index("pooled") if "pooled" in cfg.stack_models else 0] = 1.0
        return _combine_forecasts(
            history,
            grid,
            t_star,
            cfg,
            bw,
            w,
            "stacked",
            {"backtest_origins": 0, "weight_fit": "insufficient_history"},
        )
    values = []
    totals = np.zeros(n_models)
    for fields, a, p in records:
        ia, jp = grid.locate(a, p)
        ok = jp >= 0
        ia, jp = ia[ok], jp[ok]
        keep = grid.mask[ia, jp]
        values.append(np.column_stack([f.density[ia[keep], jp[keep]] for f in fields]))
        totals += np.array([f.total() for f in fields])
    design = np.concatenate(values, axis=0)
    scale = max(len(design), 1)

    def loss(w: FloatArray) -> tuple[float, FloatArray]:
        combined = design @ w + 1e-12
        value = (float(totals @ w) - float(np.log(combined).sum())) / scale
        grad = (totals - (design / combined[:, None]).sum(axis=0)) / scale
        return value, grad

    result = minimize(
        loss,
        np.full(n_models, 1 / n_models),
        jac=True,
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n_models,
        constraints={"type": "eq", "fun": lambda w: w.sum() - 1.0, "jac": lambda w: np.ones(n_models)},
        options={"ftol": 1e-11, "maxiter": 500},
    )
    fit_meta: dict[str, object] = {"weight_fit": "poisson_intensity_stacking"}
    if not result.success:
        scores = np.array(
            [sum(poisson_log_score(fields[i], a, p) for fields, a, p in records) for i in range(n_models)]
        )
        w = np.exp(scores - scores.max())
        w /= w.sum()
        fit_meta = {
            "weight_fit": "fallback_pseudo_bma",
            "weight_fit_message": str(result.message),
        }
    else:
        w = np.maximum(result.x, 0.0)
        w /= w.sum()
    return _combine_forecasts(
        history,
        grid,
        t_star,
        cfg,
        bw,
        w,
        "stacked",
        {
            "backtest_origins": len(records),
            **fit_meta,
            "held_out_log_score": -loss(w)[0] * scale,
        },
    )


Forecaster = Callable[..., IntensityField]

FORECASTERS: dict[str, Forecaster] = {
    "pooled": _pooled,
    "recent": _recent,
    "drift": _drift,
    "drift_u": _drift_u,
    "trend": _trend,
    "mixture": _mixture,
    "pseudo_bma": _pseudo_bma,
    "stacked": _stacked,
}


def forecast(
    history: History,
    grid: RepGrid,
    horizon: int,
    method: str,
    cfg: ForecastConfig | None = None,
    bw: tuple[float, float] | None = None,
) -> IntensityField:
    """Forecast the per-epoch intensity ``horizon`` epochs after the last one."""
    cfg = cfg or ForecastConfig()
    if method not in FORECASTERS:
        raise KeyError(f"unknown forecaster {method!r}; choose from {sorted(FORECASTERS)}")
    if len(history) == 0:
        raise ValueError("empty history")
    if not isinstance(horizon, (int, np.integer)) or horizon < 1:
        raise ValueError("horizon must be a positive integer")
    bw = bw or _bandwidth(history, cfg)
    t_star = float(len(history) - 1 + horizon)
    return FORECASTERS[method](history, grid, t_star, cfg, bw)
