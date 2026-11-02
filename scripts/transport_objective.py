"""Finite-grid transport tools for an exploratory geometry-aware ambiguity study."""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.optimize import linprog, minimize_scalar

from stochplace import Problem


def line_cost(alpha, p, window):
    normals = np.column_stack([np.cos(alpha), np.sin(alpha)])
    functions = normals @ window.corners.T - np.asarray(p)[:, None]
    aligned = np.max(np.abs(functions[:, None, :] - functions[None, :, :]), axis=-1)
    flipped = np.max(np.abs(functions[:, None, :] + functions[None, :, :]), axis=-1)
    return np.minimum(aligned, flipped)


def transport_distance(first, second, cost):
    first, second = np.asarray(first), np.asarray(second)
    n = len(first)
    if cost.shape != (n, n) or not np.isfinite(cost).all() or (cost < 0).any():
        raise ValueError("finite nonnegative square costs required")
    if (
        (first < 0).any()
        or (second < 0).any()
        or not np.isclose(first.sum(), 1)
        or not np.isclose(second.sum(), 1)
    ):
        raise ValueError("normalised nonnegative probability masses required")
    ones = sparse.csr_matrix(np.ones((1, n)))
    identity = sparse.eye(n, format="csr")
    constraints = sparse.vstack([sparse.kron(identity, ones), sparse.kron(ones, identity)], format="csr")
    result = linprog(
        cost.ravel(),
        A_eq=constraints,
        b_eq=np.r_[first, second],
        bounds=(0, None),
        method="highs",
        # Highly concentrated KDEs contain both exact zeros and tiny positive
        # masses. Default presolve can incorrectly declare their transport
        # constraints infeasible. Keep every mass and solve the original LP.
        options={
            "presolve": False,
            "primal_feasibility_tolerance": 1e-10,
            "dual_feasibility_tolerance": 1e-10,
        },
    )
    if not result.success:
        raise RuntimeError(f"transport calibration LP failed: {result.message}")
    if np.max(np.abs(result.eqlin.residual)) > 1e-8:
        raise RuntimeError("transport calibration LP has inaccurate marginals")
    return float(result.fun)


def transport_bound(mass, loss, cost, radius):
    """Conservative dual upper bound; the scalar minimisation is numerical."""
    mass, loss = np.asarray(mass), np.asarray(loss)
    if not np.isfinite(radius) or radius < 0:
        raise ValueError("finite nonnegative transport radius required")
    if not np.isclose(mass.sum(), 1) or (mass < 0).any():
        raise ValueError("normalised source mass required")
    if cost.shape != (len(mass), len(mass)) or not np.isfinite(cost).all() or (cost < 0).any():
        raise ValueError("finite nonnegative square costs required")
    if not np.isfinite(loss).all():
        raise ValueError("finite losses required")
    if radius == 0:
        zero_cost_losses = np.where(cost == 0, loss[None, :], -np.inf).max(axis=1)
        return float(mass @ zero_cost_losses)
    positive = cost > 0
    ratios = np.zeros_like(cost)
    np.divide(np.maximum(loss[None, :] - loss[:, None], 0), cost, out=ratios, where=positive)
    upper = float(ratios.max())
    if upper == 0:
        return float(loss.max())

    def dual(multiplier):
        return float(multiplier * radius + mass @ np.max(loss[None, :] - multiplier * cost, axis=1))

    result = minimize_scalar(
        dual, bounds=(0, upper), method="bounded", options={"xatol": 1e-10, "maxiter": 500}
    )
    if not result.success:
        raise RuntimeError("transport dual minimisation failed")
    return min(dual(0), dual(upper), dual(result.x))


class TransportProblem(Problem):
    """Greedy/exchange adapter; no continuous-gradient claim is made."""

    def __init__(self, field, model, cost, radius):
        super().__init__(field, model)
        self.cost, self.transport_radius = cost, radius
        self.normalised_mass = self.w_mean / self.w_mean.sum()

    def value(self, sensors):
        return self.w_mean.sum() * transport_bound(
            self.normalised_mass, self.miss(sensors), self.cost, self.transport_radius
        )

    def candidate_values(self, q, miss_c):
        return np.array(
            [
                self.w_mean.sum()
                * transport_bound(self.normalised_mass, q * row, self.cost, self.transport_radius)
                for row in miss_c
            ]
        )

    def gradient(self, sensors):
        raise NotImplementedError("transport study uses discrete exchange search only")
