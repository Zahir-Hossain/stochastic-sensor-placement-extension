"""Line geometry and the (alpha, p) representation space.

A straight trajectory in the plane is written in Hesse normal form

    x cos(alpha) + y sin(alpha) = p,     alpha in [0, pi),  p in R.

For a slope-intercept line ``y = m x + b`` this gives the map used by
Kim et al. (2025):

    alpha = pi/2 + arctan(m),    p = b / sqrt(1 + m^2).

The representation space is a Moebius strip: ``(alpha, p)`` and
``(alpha + pi, -p)`` describe the same line. Functions here keep
``alpha`` in ``[0, pi)`` and handle that identification explicitly.

The key identity used throughout the package is that the perpendicular
distance from a point ``(x, y)`` to the line ``(alpha, p)`` is

    d = | x cos(alpha) + y sin(alpha) - p |,

which lets every sensor/line distance be computed directly on a grid in
representation space without going back to slope-intercept form.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ._typing import FloatArray

__all__ = [
    "Window",
    "canonicalize",
    "fit_line_tls",
    "lines_to_rep",
    "point_line_distance",
    "point_line_signed",
    "rep_to_lines",
]


def lines_to_rep(slope: ArrayLike, intercept: ArrayLike) -> tuple[FloatArray, FloatArray]:
    """Map slope-intercept lines ``y = m x + b`` to ``(alpha, p)``.

    Parameters
    ----------
    slope, intercept
        Arrays of equal shape.

    Returns
    -------
    alpha, p
        ``alpha`` lies in ``(0, pi)`` because slope-intercept form cannot
        represent vertical lines.
    """
    m = np.asarray(slope, dtype=float)
    b = np.asarray(intercept, dtype=float)
    alpha = np.pi / 2 + np.arctan(m)
    p = b / np.sqrt(1.0 + m**2)
    return alpha, p


def rep_to_lines(alpha: ArrayLike, p: ArrayLike) -> tuple[FloatArray, FloatArray]:
    """Inverse of :func:`lines_to_rep` for non-vertical lines.

    Uses ``sin(alpha) = 1 / sqrt(1 + m^2)`` so that ``m = -cot(alpha)`` and
    ``b = p / sin(alpha)``.
    """
    a = np.asarray(alpha, dtype=float)
    pp = np.asarray(p, dtype=float)
    s = np.sin(a)
    if np.any(np.abs(s) < 1e-12):
        raise ValueError("vertical line (alpha = 0 or pi) has no slope-intercept form")
    m = -np.cos(a) / s
    b = pp / s
    return m, b


def canonicalize(alpha: ArrayLike, p: ArrayLike) -> tuple[FloatArray, FloatArray]:
    """Reduce any ``(alpha, p)`` to the canonical chart ``alpha in [0, pi)``.

    Uses the identification ``(alpha + pi, -p) ~ (alpha, p)``.
    """
    a = np.asarray(alpha, dtype=float)
    pp = np.asarray(p, dtype=float)
    k = np.floor(a / np.pi)
    a_c = a - k * np.pi
    # floating point can leave a_c just outside [0, pi) (e.g. denormal
    # negatives, or a_c rounding up to pi); fix the chart and the parity
    neg = a_c < 0
    a_c = np.where(neg, a_c + np.pi, a_c)
    k = np.where(neg, k - 1, k)
    big = a_c >= np.pi
    a_c = np.where(big, a_c - np.pi, a_c)
    k = np.where(big, k + 1, k)
    p_c = np.where(np.mod(k, 2) == 0, pp, -pp)
    return a_c, p_c


def point_line_signed(x: ArrayLike, y: ArrayLike, alpha: ArrayLike, p: ArrayLike) -> FloatArray:
    """Signed offset ``x cos(alpha) + y sin(alpha) - p`` (broadcasting)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    alpha = np.asarray(alpha, dtype=float)
    p = np.asarray(p, dtype=float)
    return x * np.cos(alpha) + y * np.sin(alpha) - p


def point_line_distance(x: ArrayLike, y: ArrayLike, alpha: ArrayLike, p: ArrayLike) -> FloatArray:
    """Perpendicular distance from point(s) ``(x, y)`` to line(s) ``(alpha, p)``."""
    return np.abs(point_line_signed(x, y, alpha, p))


def fit_line_tls(xy: ArrayLike) -> tuple[float, float, float]:
    """Total-least-squares line fit to a set of 2-D points.

    Returns
    -------
    alpha, p
        Canonical representation of the best-fit line.
    linearity
        ``1 - lambda_min / lambda_max`` of the point covariance, in ``[0, 1]``.
        Values near 1 mean the points lie close to a straight line.
    """
    pts = np.asarray(xy, dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2 or pts.shape[0] < 2:
        raise ValueError("xy must have shape (n >= 2, 2)")
    c = pts.mean(axis=0)
    cov = np.cov((pts - c).T)
    evals, evecs = np.linalg.eigh(cov)  # ascending
    normal = evecs[:, 0]
    if normal[1] < 0 or (normal[1] == 0 and normal[0] < 0):
        normal = -normal
    alpha = float(np.arctan2(normal[1], normal[0]))
    p = float(normal @ c)
    a_c, p_c = canonicalize(alpha, p)
    lam_max = float(evals[-1])
    linearity = 1.0 - float(evals[0]) / lam_max if lam_max > 0 else 0.0
    return float(a_c), float(p_c), linearity


@dataclass(frozen=True)
class Window:
    """Axis-aligned rectangular region where sensors may be placed."""

    xmin: float
    xmax: float
    ymin: float
    ymax: float

    def __post_init__(self) -> None:
        if not (self.xmax > self.xmin and self.ymax > self.ymin):
            raise ValueError("Window must have positive width and height")

    @property
    def corners(self) -> FloatArray:
        return np.array(
            [
                [self.xmin, self.ymin],
                [self.xmax, self.ymin],
                [self.xmax, self.ymax],
                [self.xmin, self.ymax],
            ]
        )

    @property
    def p_bound(self) -> float:
        """Largest ``|p|`` of any line that touches the window."""
        return float(np.max(np.hypot(self.corners[:, 0], self.corners[:, 1])))

    def grid(self, dx: float, dy: float | None = None) -> FloatArray:
        """Regular candidate grid (inclusive of edges) as an ``(n, 2)`` array."""
        dy = dx if dy is None else dy
        xs = np.arange(self.xmin, self.xmax + 1e-9, dx)
        ys = np.arange(self.ymin, self.ymax + 1e-9, dy)
        gx, gy = np.meshgrid(xs, ys)
        return np.column_stack([gx.ravel(), gy.ravel()])

    def contains(self, xy: ArrayLike) -> NDArray[np.bool_]:
        pts = np.atleast_2d(np.asarray(xy, dtype=float))
        return (
            (pts[:, 0] >= self.xmin)
            & (pts[:, 0] <= self.xmax)
            & (pts[:, 1] >= self.ymin)
            & (pts[:, 1] <= self.ymax)
        )

    def line_hits(self, alpha: ArrayLike, p: ArrayLike) -> NDArray[np.bool_]:
        """True where line ``(alpha, p)`` intersects the window."""
        a = np.asarray(alpha, dtype=float)[..., None]
        pp = np.asarray(p, dtype=float)[..., None]
        proj = self.corners[:, 0] * np.cos(a) + self.corners[:, 1] * np.sin(a)
        return (pp[..., 0] >= proj.min(axis=-1)) & (pp[..., 0] <= proj.max(axis=-1))

    def sample_uniform(self, n: int, rng: np.random.Generator) -> FloatArray:
        return np.column_stack([rng.uniform(self.xmin, self.xmax, n), rng.uniform(self.ymin, self.ymax, n)])
