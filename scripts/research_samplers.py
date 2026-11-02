"""Frozen candidate laws for evaluation only; neither replaces the default sampler."""

from __future__ import annotations

from importlib import import_module

import numpy as np

from stochplace.forecast import ForecastConfig, forecast
from stochplace.grid import IntensityField
from stochplace.intensity import kde_intensity

fm = import_module("stochplace.forecast")


def weighted_candidate(
    history, grid, horizon: int, config: ForecastConfig, current: IntensityField, seed: int
) -> IntensityField:
    bandwidth = fm._bandwidth(history, config)
    t_star = len(history) - 1 + horizon
    draws = np.zeros((config.n_samples, *grid.shape))
    for index, model in enumerate(config.stack_models):
        field = fm.FORECASTERS[model](history, grid, t_star, config, bandwidth)
        weight = current.meta["weights"][model]
        if field.samples is None:
            draws += weight * field.density
        else:
            rng = np.random.default_rng([seed, 1337, index])
            selected = rng.integers(0, len(field.samples), config.n_samples)
            draws += weight * field.samples[selected]
    return IntensityField(grid, current.density.copy(), samples=draws, label="weighted_candidate")


def residual_candidate(
    history, grid, horizon: int, config: ForecastConfig, current: IntensityField, seed: int
) -> IntensityField:
    factors, backtests = [], []
    for target in range(max(0, len(history) - config.backtest_epochs), len(history)):
        length = target - horizon + 1
        if length < 3:
            continue
        prefix = history[:length]
        fitted = forecast(prefix, grid, horizon, "stacked", config)
        backtests.append(
            {
                "target": target,
                "history_epochs": length,
                "weight_fit": fitted.meta.get("weight_fit", "not_recorded"),
                "weight_fit_message": fitted.meta.get("weight_fit_message", ""),
            }
        )
        bandwidth = fm._bandwidth(prefix, config)
        observed = kde_intensity(*history[target], grid, bandwidth=bandwidth)
        floor = 1e-12 * max(float(fitted.density[grid.mask].mean()), 1.0)
        factors.append((observed.density + floor) / (fitted.density + floor))
    if not factors:
        raise ValueError("residual candidate requires usable chronological backtests")
    errors = np.stack(factors)
    errors /= errors.mean(axis=0)
    selected = np.random.default_rng([seed, 7331]).integers(0, len(errors), config.n_samples)
    draws = current.density[None] * errors[selected]
    return IntensityField(
        grid,
        current.density.copy(),
        samples=draws,
        label="residual_candidate",
        meta={"residual_backtests": backtests},
    )
