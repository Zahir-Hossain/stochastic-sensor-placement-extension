"""Sensor placement algorithms and baselines."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize

from ._typing import FloatArray
from .geometry import Window
from .objective import Problem

__all__ = [
    "Placement",
    "brute_force",
    "fence_placement",
    "greedy",
    "random_placement",
    "refine",
    "solve",
    "swap_refine",
]


@dataclass
class Placement:
    """Selected sensor positions plus diagnostics."""

    sensors: FloatArray
    value: float
    method: str
    history: list[float] = field(default_factory=list)
    meta: dict[str, object] = field(default_factory=dict)


def greedy(problem: Problem, candidates: FloatArray, k: int) -> Placement:
    """Greedy selection from a finite candidate set.

    At each step the candidate that most reduces the objective is added.
    For the ``expected`` objective the detected mass is monotone
    submodular, so the result is within ``1 - 1/e`` of the best ``k``-subset
    of ``candidates`` (Nemhauser, Wolsey and Fisher, 1978). Ties go to the
    first candidate in order, matching the original MATLAB script.
    """
    cand = np.asarray(candidates, dtype=float)
    if k < 1 or k > len(cand):
        raise ValueError("need 1 <= k <= number of candidates")
    miss_c = 1.0 - problem.detect_matrix(cand)  # (m, n)
    q = np.ones(problem.n_cells)
    available = np.ones(len(cand), dtype=bool)
    chosen: list[int] = []
    hist: list[float] = []
    for _ in range(k):
        vals = problem.candidate_values(q, miss_c)
        vals = np.where(available, vals, np.inf)
        j = int(np.argmin(vals))
        chosen.append(j)
        available[j] = False
        q = q * miss_c[j]
        hist.append(float(vals[j]))
    sensors = cand[chosen]
    return Placement(sensors, problem.value(sensors), "greedy", hist, {"indices": chosen})


def refine(problem: Problem, start: Placement, window: Window, maxiter: int = 200) -> Placement:
    """Continuous refinement of sensor coordinates by L-BFGS-B.

    Starts from ``start`` (usually a greedy solution) and keeps sensors
    inside ``window``. Never returns a worse solution than ``start``.
    """
    if not problem.model.smooth or problem.objective == "tv":
        return start
    x0 = np.asarray(start.sensors, dtype=float).ravel()
    k = len(start.sensors)
    bounds = [(window.xmin, window.xmax), (window.ymin, window.ymax)] * k

    def fun(x: FloatArray) -> tuple[float, FloatArray]:
        v, g = problem.gradient(x.reshape(k, 2))
        return v, g.ravel()

    res = minimize(fun, x0, jac=True, method="L-BFGS-B", bounds=bounds, options={"maxiter": maxiter})
    s = res.x.reshape(k, 2)
    v = problem.value(s)
    if v > start.value:
        return start
    return Placement(
        s,
        v,
        start.method + "+refine",
        start.history,
        {**start.meta, "nit": int(res.nit), "converged": bool(res.success), "message": str(res.message)},
    )


def swap_refine(problem: Problem, candidates: FloatArray, start: Placement, max_passes: int = 5) -> Placement:
    """Improve a grid placement by exact one-sensor exchanges.

    Appropriate for the nonsmooth TV objective. Every accepted exchange
    decreases that objective; this is a local-search heuristic, without
    the expected-mass greedy approximation guarantee.
    """
    cand = np.asarray(candidates, dtype=float)
    raw_indices = start.meta.get("indices", [])
    if not isinstance(raw_indices, list):
        raise ValueError("candidate indices must be a list")
    chosen = [int(j) for j in raw_indices]
    if not chosen or len(chosen) != len(start.sensors):
        raise ValueError("swap refinement needs candidate indices from greedy")
    miss_c = 1.0 - problem.detect_matrix(cand)
    best = start.value
    values = [best]
    passes = 0
    for _pass in range(max_passes):
        passes = _pass + 1
        improved = False
        for slot in range(len(chosen)):
            others = [j for i, j in enumerate(chosen) if i != slot]
            q = np.prod(miss_c[others], axis=0) if others else np.ones(problem.n_cells)
            candidate_values = problem.candidate_values(q, miss_c)
            candidate_values[others] = np.inf
            j = int(np.argmin(candidate_values))
            value = float(candidate_values[j])
            if value < best - 1e-10 * max(1.0, abs(best)):
                chosen[slot], best = j, value
                values.append(best)
                improved = True
        if not improved:
            break
    sensors = cand[chosen]
    return Placement(
        sensors, problem.value(sensors), start.method + "+swap", values, {"indices": chosen, "passes": passes}
    )


def solve(
    problem: Problem,
    candidates: FloatArray,
    k: int,
    window: Window,
    *,
    do_refine: bool = True,
) -> Placement:
    """Greedy selection followed by optional continuous refinement."""
    pl = greedy(problem, candidates, k)
    if do_refine and problem.objective == "tv":
        return swap_refine(problem, candidates, pl)
    return refine(problem, pl, window) if do_refine else pl


def random_placement(problem: Problem, window: Window, k: int, rng: np.random.Generator) -> Placement:
    s = window.sample_uniform(k, rng)
    return Placement(s, problem.value(s), "random")


def fence_placement(problem: Problem, window: Window, k: int) -> Placement:
    """Evenly spaced sensors along the long mid-line of the window."""
    w = window.xmax - window.xmin
    h = window.ymax - window.ymin
    t = (np.arange(k) + 0.5) / k
    if w >= h:
        s = np.column_stack([window.xmin + t * w, np.full(k, 0.5 * (window.ymin + window.ymax))])
    else:
        s = np.column_stack([np.full(k, 0.5 * (window.xmin + window.xmax)), window.ymin + t * h])
    return Placement(s, problem.value(s), "fence")


def brute_force(problem: Problem, candidates: FloatArray, k: int, max_subsets: int = 200_000) -> Placement:
    """Exhaustive search over all ``k``-subsets (small instances only)."""
    cand = np.asarray(candidates, dtype=float)
    from math import comb

    n_sub = comb(len(cand), k)
    if n_sub > max_subsets:
        raise ValueError(f"{n_sub} subsets exceeds max_subsets={max_subsets}")
    miss_c = 1.0 - problem.detect_matrix(cand)
    best_v = np.inf
    best: tuple[int, ...] = ()
    for sub in itertools.combinations(range(len(cand)), k):
        q = np.prod(miss_c[list(sub)], axis=0)
        if problem.objective == "tv":
            from .risk import tv_values

            v = float(tv_values(problem.w_mean, q, problem.radius))
        elif problem.objective == "expected":
            v = float(problem.w_mean @ q)
        else:
            v = float(problem._reduce((problem.W @ q)[None])[0])
        if v < best_v:
            best_v, best = v, sub
    return Placement(cand[list(best)], best_v, "brute_force", meta={"indices": list(best)})
