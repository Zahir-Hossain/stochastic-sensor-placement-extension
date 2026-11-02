"""Finite-distribution risk measures with explicit tail and mass budgets.

Total variation uses half the L1 distance between equal-total probability
vectors. For count masses the transport budget is ``radius * total``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ._typing import FloatArray

__all__ = ["AdversarialMass", "cvar_weights", "tv_adversary", "tv_values"]


def cvar_weights(losses: FloatArray, beta: float) -> FloatArray:
    """Weights of the upper ``1-beta`` tail of an equally weighted sample.

    Includes a fractional boundary observation. At a tied quantile this
    returns one valid subgradient; CVaR need not be differentiable there.
    """
    x = np.asarray(losses, dtype=float)
    if x.ndim < 1 or x.shape[-1] == 0 or not np.all(np.isfinite(x)):
        raise ValueError("losses need a nonempty finite sample axis")
    if not np.isfinite(beta) or not 0 <= beta < 1:
        raise ValueError("beta must be in [0, 1)")
    tail = (1 - beta) * x.shape[-1]
    ranked_weights = np.clip(tail - np.arange(x.shape[-1]), 0.0, 1.0) / tail
    order = np.argsort(-x, axis=-1, kind="stable")
    weights = np.empty_like(x)
    np.put_along_axis(weights, order, np.broadcast_to(ranked_weights, x.shape), axis=-1)
    return weights


@dataclass(frozen=True)
class AdversarialMass:
    """Worst-case equal-total cell masses and the attained linear loss."""

    value: float
    mass: FloatArray
    moved_mass: float
    total_variation: float


def _validate_tv(mass: FloatArray, losses: FloatArray, radius: float) -> tuple[FloatArray, FloatArray]:
    m = np.asarray(mass, dtype=float)
    q = np.asarray(losses, dtype=float)
    if m.ndim != 1 or len(m) == 0 or q.shape[-1:] != m.shape:
        raise ValueError("mass must be a nonempty vector matching the losses' last axis")
    if np.any(m < 0) or not np.all(np.isfinite(m)) or not np.all(np.isfinite(q)):
        raise ValueError("mass must be non-negative; mass and losses must be finite")
    if not np.isfinite(radius) or not 0 <= radius <= 1:
        raise ValueError("radius must be in [0, 1]")
    return m, q


def tv_values(mass: FloatArray, losses: FloatArray, radius: float) -> FloatArray:
    """Exact worst-case linear losses over an equal-total TV ball.

    Sort donors by increasing loss, move at most ``radius * sum(mass)``
    mass to a maximum-loss cell, and stop once all remaining donors have
    that same loss. Vectorised over all axes preceding the cell axis.
    """
    m, q = _validate_tv(mass, losses, radius)
    order = np.argsort(q, axis=-1, kind="stable")
    ranked_q = np.take_along_axis(q, order, axis=-1)
    ranked_m = np.take_along_axis(np.broadcast_to(m, q.shape), order, axis=-1)
    before = np.cumsum(ranked_m, axis=-1) - ranked_m
    removed = np.minimum(ranked_m, np.maximum(radius * m.sum() - before, 0.0))
    gain = np.sum(removed * (ranked_q[..., -1:] - ranked_q), axis=-1)
    return np.asarray(q @ m + gain)


def tv_adversary(mass: FloatArray, losses: FloatArray, radius: float) -> AdversarialMass:
    """Construct an optimizer of the TV-ball support problem.

    This solves the inner adversarial problem exactly on the supplied
    grid. It does not certify global optimality of the outer sensor plan.
    """
    m, q = _validate_tv(mass, losses, radius)
    if q.ndim != 1:
        raise ValueError("tv_adversary needs one loss vector")
    order = np.argsort(q, kind="stable")
    qmax = q.max()
    donors = m[order].copy()
    donors[q[order] == qmax] = 0.0
    budget = min(radius * m.sum(), float(donors.sum()))
    before = np.cumsum(donors) - donors
    removed = np.minimum(donors, np.maximum(budget - before, 0.0))
    out = m.copy()
    out[order] -= removed
    moved = float(removed.sum())
    out[int(np.argmax(q))] += moved
    total = float(m.sum())
    return AdversarialMass(float(out @ q), out, moved, moved / total if total > 0 else 0.0)
