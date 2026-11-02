"""Faithful Python port of the original v0.1 MATLAB toy simulation.

``legacy/matlab/sensor_placement_simulation.m`` is kept unchanged in the
repository. This module reproduces its numerical pipeline (without the
figures) so the port can be checked against GNU Octave in the test
suite, and so the limitations of v0.1 can be shown side by side with
the v2 method.

Known limitations of v0.1, reproduced deliberately here:

* the intensity maps are computed but never used by the placement;
  greedy works on the raw route list;
* each scenario's intensity map uses its own grid, so maps cannot be
  combined into ``lambda_E``;
* each placement is scored on its own route set, so the reported
  "normalized miss scores" are not comparable across scenarios.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ._typing import FloatArray

__all__ = ["LegacyResult", "legacy_candidates", "legacy_greedy", "legacy_pipeline", "legacy_routes"]


def legacy_routes(rng: np.random.Generator, n: int = 250) -> tuple[FloatArray, FloatArray]:
    """Historical routes with the v0.1 parameters (numpy RNG, not MATLAB's)."""
    slope = 0.2 + 0.1 * rng.standard_normal(n)
    intercept = 0.0 + 0.5 * rng.standard_normal(n)
    return slope, intercept


def legacy_candidates() -> FloatArray:
    """Candidate grid in MATLAB ``meshgrid(...)(:)`` (column-major) order."""
    xs = np.arange(-10, 11, 1.0)
    ys = np.arange(-5, 6, 1.0)
    sx, sy = np.meshgrid(xs, ys)  # rows = y, cols = x, like MATLAB
    return np.column_stack([sx.ravel(order="F"), sy.ravel(order="F")])


def legacy_greedy(
    slope: FloatArray,
    intercept: FloatArray,
    candidates: FloatArray,
    k: int = 5,
    rho: float = 0.95,
    r: float = 1.5,
) -> tuple[FloatArray, float]:
    """Greedy loop of v0.1: minimise the summed miss probability of routes."""
    cand = candidates.copy()
    q = np.ones(len(slope))
    chosen = []
    for _ in range(k):
        best_score = np.inf
        best_j = -1
        best_q = q
        for j in range(len(cand)):
            sx, sy = cand[j]
            d = np.abs(slope * sx - sy + intercept) / np.sqrt(slope**2 + 1)
            pd = rho * np.exp(-(d**2) / (2 * r**2))
            nq = q * (1 - pd)
            score = nq.sum()
            if score < best_score:  # strict, first minimum wins (as in MATLAB)
                best_score, best_j, best_q = score, j, nq
        chosen.append(cand[best_j].copy())
        q = best_q
        cand = np.delete(cand, best_j, axis=0)
    return np.array(chosen), float(q.sum())


@dataclass
class LegacyResult:
    historical_sensors: FloatArray
    future_sensors: FloatArray
    uncertainty_sensors: FloatArray
    normalized_miss: dict[str, float]
    routes: dict[str, tuple[FloatArray, FloatArray]]


def legacy_pipeline(slope: FloatArray, intercept: FloatArray, k: int = 5) -> LegacyResult:
    """Run the three v0.1 scenarios on given historical routes."""
    cand = legacy_candidates()
    hs, hm = legacy_greedy(slope, intercept, cand, k)
    f_slope = slope + 0.05
    f_int = intercept + 0.5
    fs, fm = legacy_greedy(f_slope, f_int, cand, k)
    base_s = np.concatenate([slope, f_slope])
    base_b = np.concatenate([intercept, f_int])
    us_list, ub_list = [], []
    for ds in (-0.03, 0.0, 0.03):
        for db in (-0.4, 0.0, 0.4):
            us_list.append(base_s + ds)
            ub_list.append(base_b + db)
    u_s = np.concatenate(us_list)
    u_b = np.concatenate(ub_list)
    uss, um = legacy_greedy(u_s, u_b, cand, k)
    n = len(slope)
    return LegacyResult(
        hs,
        fs,
        uss,
        {"historical": hm / n, "prediction": fm / n, "uncertainty": um / len(u_s)},
        {"historical": (slope, intercept), "prediction": (f_slope, f_int), "uncertainty": (u_s, u_b)},
    )
