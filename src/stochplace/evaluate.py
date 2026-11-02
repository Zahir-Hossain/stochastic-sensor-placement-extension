"""Scoring placements against the realised future."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ._typing import FloatArray
from .grid import IntensityField
from .objective import Problem, miss_probability_lines
from .sensors import SensorModel

__all__ = ["Score", "bootstrap_ci", "score_on_lines", "score_on_truth"]


@dataclass
class Score:
    """Performance of a sensor set against the true future intensity.

    Attributes
    ----------
    missed
        Expected number of undetected trajectories per epoch.
    total
        Expected number of trajectories per epoch.
    detection_rate
        ``1 - missed / total``.
    void_probability
        ``exp(-missed)``: probability that *no* trajectory slips through
        in an epoch.
    """

    missed: float
    total: float

    @property
    def detection_rate(self) -> float:
        return 1.0 - self.missed / self.total if self.total > 0 else float("nan")

    @property
    def void_probability(self) -> float:
        return float(np.exp(-self.missed))


def score_on_truth(sensors: FloatArray, truth: IntensityField, model: SensorModel) -> Score:
    """Cell-centre quadrature of detection under a known grid intensity."""
    prob = Problem(truth, model)
    return Score(float(prob.lambda_miss(sensors)), truth.total())


def score_on_lines(sensors: FloatArray, alpha: FloatArray, p: FloatArray, model: SensorModel) -> Score:
    """Score on a finite set of realised lines (no grid involved)."""
    q = miss_probability_lines(sensors, alpha, p, model)
    return Score(float(q.sum()), float(len(alpha)))


def bootstrap_ci(
    x: FloatArray, n_boot: int = 2000, level: float = 0.95, rng: np.random.Generator | None = None
) -> tuple[float, float, float]:
    """Mean and percentile bootstrap confidence interval."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    rng = rng or np.random.default_rng(12345)
    idx = rng.integers(0, len(x), (n_boot, len(x)))
    means = x[idx].mean(axis=1)
    lo, hi = np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(x.mean()), float(lo), float(hi)
