r"""Void-probability objectives for barrier coverage.

Model
-----
Trajectories crossing the barrier form a Poisson line process with
intensity :math:`\lambda(\alpha, p)`. Each trajectory is missed by a
sensor network :math:`S` independently with probability

.. math:: q_S(\alpha, p) = \prod_{s \in S} \bigl(1 - P_D(d_s(\alpha, p))\bigr).

By Poisson thinning, the undetected trajectories form a Poisson process
with intensity :math:`\lambda q_S`, so

.. math::
    \Lambda_{\text{miss}}(S;\lambda) = \int \lambda\, q_S \, d\alpha\, dp,
    \qquad
    P(\text{no undetected trajectory}) = e^{-\Lambda_{\text{miss}}(S;\lambda)}.

This void probability is the objective of Kim et al. (2025). For a
known intensity, maximising it is the same as minimising
:math:`\Lambda_{\text{miss}}`.

When the intensity itself is uncertain (posterior or forecast samples
:math:`\lambda^{(1)}, \dots, \lambda^{(K)}`) three objectives are
offered, all *minimised*:

``expected``
    :math:`E[\Lambda_{\text{miss}}] = \Lambda_{\text{miss}}(S; E\lambda)`
    (linearity). Monotone supermodular in :math:`S`, so greedy enjoys
    the :math:`(1 - 1/e)` guarantee on the detected mass.
``void``
    :math:`-\log E[e^{-\Lambda_{\text{miss}}}]`: maximises the expected
    void probability. This is a soft minimum of sample miss counts and
    gives more influence to favourable, low-miss futures; it is not a
    worst-case or risk-averse loss.
``cvar``
    Conditional value-at-risk of :math:`\Lambda_{\text{miss}}` at level
    ``beta``: the mean over the worst ``1 - beta`` fraction of samples.
``tv``
    Worst expected miss count under equal-total intensity perturbations
    with total variation distance at most ``radius`` on the active grid.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np

from ._typing import FloatArray
from .grid import IntensityField
from .risk import cvar_weights, tv_adversary, tv_values
from .sensors import SensorModel

__all__ = ["OBJECTIVES", "Problem", "miss_probability_lines"]

OBJECTIVES = ("expected", "void", "cvar", "tv")


def miss_probability_lines(
    sensors: FloatArray, alpha: FloatArray, p: FloatArray, model: SensorModel
) -> FloatArray:
    """Exact miss probability of each line ``(alpha_i, p_i)`` for a network."""
    sensors = np.atleast_2d(np.asarray(sensors, dtype=float))
    alpha = np.asarray(alpha, dtype=float)
    p = np.asarray(p, dtype=float)
    q = np.ones_like(alpha)
    for xs, ys in sensors:
        s = xs * np.cos(alpha) + ys * np.sin(alpha) - p
        q = q * (1.0 - model.prob(s * s))
    return q


@dataclass
class Problem:
    """A placement problem on the active cells of an intensity field.

    Parameters
    ----------
    field
        Intensity used for planning. If it carries ``samples`` they are
        used by the ``void`` and ``cvar`` objectives.
    model
        Sensor detection model.
    objective
        One of ``expected``, ``void``, ``cvar``.
    beta
        CVaR level (only for ``cvar``).
    """

    field: IntensityField
    model: SensorModel
    objective: str = "expected"
    beta: float = 0.9
    radius: float = 0.05

    def __post_init__(self) -> None:
        if self.objective not in OBJECTIVES:
            raise ValueError(f"objective must be one of {OBJECTIVES}")
        if not (0 <= self.beta < 1):
            raise ValueError("beta must be in [0, 1)")
        if not np.isfinite(self.radius) or not 0 <= self.radius <= 1:
            raise ValueError("radius must be in [0, 1]")
        if self.objective in ("void", "cvar"):
            if self.field.label in ("stacked", "pseudo_bma") and self.field.samples is not None:
                warnings.warn(
                    "This objective uses component-sampled forecast uncertainty that has not "
                    "been validated for calibration. Interpret the result as a sensitivity analysis. "
                    "The sampling weights are not established posterior model probabilities.",
                    UserWarning,
                    stacklevel=2,
                )
            elif self.field.label == "mixture" and self.field.samples is None:
                warnings.warn(
                    "The fixed mixture contains no uncertainty samples; this objective uses only "
                    "its single mean field and does not quantify predictive uncertainty.",
                    UserWarning,
                    stacklevel=2,
                )
        g = self.field.grid
        m = g.mask
        a, pp = g.mesh()
        self.alpha = a[m]
        self.p = pp[m]
        self.cos = np.cos(self.alpha)
        self.sin = np.sin(self.alpha)
        self.w_mean = self.field.mass[m]
        self.W = self.field.sample_mass[:, m]  # (K, n)

    # ------------------------------------------------------------------
    @property
    def n_cells(self) -> int:
        return int(self.alpha.size)

    def signed(self, sensors: FloatArray) -> FloatArray:
        """Signed offsets, shape ``(k, n_cells)``."""
        s = np.atleast_2d(np.asarray(sensors, dtype=float))
        return s[:, :1] * self.cos[None] + s[:, 1:2] * self.sin[None] - self.p[None]

    def detect_matrix(self, sensors: FloatArray) -> FloatArray:
        """Detection probabilities, shape ``(k, n_cells)``."""
        s = self.signed(sensors)
        return self.model.prob(s * s)

    def miss(self, sensors: FloatArray) -> FloatArray:
        """Network miss probability per cell."""
        if len(np.atleast_2d(sensors)) == 0 or np.size(sensors) == 0:
            return np.ones(self.n_cells)
        return np.prod(1.0 - self.detect_matrix(sensors), axis=0)

    def lambda_miss(self, sensors: FloatArray, *, per_sample: bool = False) -> FloatArray | float:
        """Expected number of undetected trajectories per epoch."""
        q = self.miss(sensors)
        if per_sample:
            return self.W @ q
        return float(self.w_mean @ q)

    # ------------------------------------------------------------------
    def _reduce(self, lam_s: FloatArray) -> FloatArray:
        """Map per-sample miss counts ``(..., K)`` to the scalar objective."""
        if self.objective == "void":
            mn = lam_s.min(axis=-1, keepdims=True)
            return mn[..., 0] - np.log(np.mean(np.exp(-(lam_s - mn)), axis=-1))
        if self.objective == "cvar":
            return np.asarray(np.sum(cvar_weights(lam_s, self.beta) * lam_s, axis=-1))
        raise AssertionError

    def value(self, sensors: FloatArray) -> float:
        """Objective value (lower is better)."""
        if self.objective == "expected":
            return float(self.lambda_miss(sensors))
        if self.objective == "tv":
            return float(tv_values(self.w_mean, self.miss(sensors), self.radius))
        lam_s = np.asarray(self.lambda_miss(sensors, per_sample=True))
        return float(self._reduce(lam_s))

    def candidate_values(self, q: FloatArray, miss_c: FloatArray) -> FloatArray:
        """Objective after adding each candidate to a network with miss ``q``.

        ``miss_c`` is ``1 - P_D`` for the candidates, shape ``(m, n)``.
        """
        if self.objective == "expected":
            return miss_c @ (self.w_mean * q)
        if self.objective == "tv":
            return tv_values(self.w_mean, miss_c * q, self.radius)
        lam = (self.W * q[None]) @ miss_c.T  # (K, m)
        return self._reduce(lam.T)

    # ------------------------------------------------------------------
    def gradient(self, sensors: FloatArray) -> tuple[float, FloatArray]:
        """Objective value and gradient w.r.t. sensor coordinates.

        Requires a smooth sensor model.
        """
        if not self.model.smooth:
            raise ValueError("gradient needs a smooth sensor model")
        s_xy = np.atleast_2d(np.asarray(sensors, dtype=float))
        k = len(s_xy)
        sg = self.signed(s_xy)
        d2 = sg * sg
        P = self.model.prob(d2)
        M = 1.0 - P
        # leave-one-out products of M over sensors
        pre = np.ones_like(M)
        suf = np.ones_like(M)
        for i in range(1, k):
            pre[i] = pre[i - 1] * M[i - 1]
        for i in range(k - 2, -1, -1):
            suf[i] = suf[i + 1] * M[i + 1]
        others = pre * suf
        q = others[0] * M[0]
        dP_dd2 = self.model.dprob_dd2(d2)
        # dq/dx_k = -others_k * dP/dd2 * 2 s * cos ; same with sin for y
        base = -others * dP_dd2 * 2.0 * sg  # (k, n)
        dq_dx = base * self.cos[None]
        dq_dy = base * self.sin[None]
        if self.objective == "tv":
            worst = tv_adversary(self.w_mean, q, self.radius)
            return worst.value, np.column_stack([dq_dx @ worst.mass, dq_dy @ worst.mass])
        if self.objective == "expected":
            val = float(self.w_mean @ q)
            gx = dq_dx @ self.w_mean
            gy = dq_dy @ self.w_mean
            return val, np.column_stack([gx, gy])
        lam_s = self.W @ q  # (K,)
        gl_x = self.W @ dq_dx.T  # (K, k)
        gl_y = self.W @ dq_dy.T
        if self.objective == "void":
            z = -(lam_s - lam_s.min())
            wts = np.exp(z) / np.exp(z).sum()
        else:
            wts = cvar_weights(lam_s, self.beta)
        val = float(self._reduce(lam_s[None])[0])
        return val, np.column_stack([wts @ gl_x, wts @ gl_y])
