"""Discretisation of representation space and trajectory intensity fields."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np
import scipy.sparse as sp
from numpy.typing import NDArray

from ._typing import FloatArray
from .geometry import Window

__all__ = ["IntensityField", "RepGrid"]


@dataclass(frozen=True)
class RepGrid:
    """Regular grid over ``alpha in [0, pi)`` and ``p in [-p_max, p_max]``.

    The full ``alpha`` range is always used so that the Moebius
    identification ``(0, p) ~ (pi, -p)`` can be applied at the seam.

    Attributes
    ----------
    window
        Sensor deployment region. Lines that miss the window (plus
        ``margin``) are excluded through :attr:`mask`.
    n_alpha, n_p
        Number of cells along each axis.
    margin
        Lines within ``margin`` of the window still count as relevant.
    """

    window: Window
    n_alpha: int = 72
    n_p: int = 64
    margin: float = 0.0
    p_max: float | None = None

    def __post_init__(self) -> None:
        if self.n_alpha < 4 or self.n_p < 4:
            raise ValueError("grid needs at least 4 cells per axis")
        if self.p_max is None:
            object.__setattr__(self, "p_max", self.window.p_bound + self.margin)

    # ----- axes -------------------------------------------------------
    @property
    def alpha_edges(self) -> FloatArray:
        return np.linspace(0.0, np.pi, self.n_alpha + 1)

    @property
    def p_edges(self) -> FloatArray:
        assert self.p_max is not None
        return np.linspace(-self.p_max, self.p_max, self.n_p + 1)

    @property
    def alpha(self) -> FloatArray:
        e = self.alpha_edges
        return 0.5 * (e[:-1] + e[1:])

    @property
    def p(self) -> FloatArray:
        e = self.p_edges
        return 0.5 * (e[:-1] + e[1:])

    @property
    def d_alpha(self) -> float:
        return float(np.pi / self.n_alpha)

    @property
    def d_p(self) -> float:
        assert self.p_max is not None
        return float(2 * self.p_max / self.n_p)

    @property
    def cell_area(self) -> float:
        return self.d_alpha * self.d_p

    @property
    def shape(self) -> tuple[int, int]:
        return (self.n_alpha, self.n_p)

    def mesh(self) -> tuple[FloatArray, FloatArray]:
        """``(A, P)`` meshes with ``indexing='ij'`` (alpha first)."""
        a, pp = np.meshgrid(self.alpha, self.p, indexing="ij")
        return a, pp

    @property
    def mask(self) -> NDArray[np.bool_]:
        """Cells whose central line passes within ``margin`` of the window."""
        a, pp = self.mesh()
        c = self.window.corners
        proj = c[:, 0][None, None, :] * np.cos(a)[..., None] + c[:, 1][None, None, :] * np.sin(a)[..., None]
        lo = proj.min(axis=-1) - self.margin
        hi = proj.max(axis=-1) + self.margin
        return (pp >= lo) & (pp <= hi)

    # ----- lattice structure -----------------------------------------
    def laplacian(self) -> sp.csr_matrix:
        """Graph Laplacian of the 4-neighbour lattice with Moebius wrap.

        Cell ``(0, j)`` neighbours cell ``(n_alpha - 1, n_p - 1 - j)``
        because ``(alpha, p) ~ (alpha + pi, -p)``.
        """
        na, npp = self.shape
        idx = np.arange(na * npp).reshape(na, npp)
        rows: list[NDArray[np.int64]] = []
        cols: list[NDArray[np.int64]] = []
        # neighbours along p
        rows.append(idx[:, :-1].ravel())
        cols.append(idx[:, 1:].ravel())
        # neighbours along alpha
        rows.append(idx[:-1, :].ravel())
        cols.append(idx[1:, :].ravel())
        # Moebius seam
        rows.append(idx[0, :])
        cols.append(idx[na - 1, ::-1])
        r = np.concatenate(rows)
        c = np.concatenate(cols)
        n = na * npp
        adj = sp.coo_matrix((np.ones(len(r)), (r, c)), shape=(n, n))
        adj = ((adj + adj.T) > 0).astype(float)
        deg = np.asarray(adj.sum(axis=1)).ravel()
        return sp.csr_matrix(sp.diags(deg) - adj)

    def locate(self, alpha: FloatArray, p: FloatArray) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
        """Cell indices of points; points outside the p-range get index -1."""
        ia = np.clip((np.asarray(alpha) / self.d_alpha).astype(int), 0, self.n_alpha - 1)
        assert self.p_max is not None
        jp = np.floor((np.asarray(p) + self.p_max) / self.d_p).astype(int)
        jp = np.where((jp < 0) | (jp >= self.n_p), -1, jp)
        return ia, jp

    def histogram(self, alpha: FloatArray, p: FloatArray, weights: FloatArray | None = None) -> FloatArray:
        """Counts per cell (points outside the p-range are dropped)."""
        ia, jp = self.locate(alpha, p)
        ok = jp >= 0
        w = np.ones(len(ia)) if weights is None else np.asarray(weights, dtype=float)
        out = np.zeros(self.shape)
        np.add.at(out, (ia[ok], jp[ok]), w[ok])
        return out


@dataclass
class IntensityField:
    """Trajectory intensity on a :class:`RepGrid`.

    ``density`` is the expected number of trajectories per unit
    ``alpha * p`` area per epoch, so the expected count in a cell is
    ``density * grid.cell_area``. Cells outside ``grid.mask`` are zero.

    ``samples`` optionally holds draws from a predictive or posterior
    distribution over intensity (shape ``(S, n_alpha, n_p)``). Its mean
    should match ``density``; robust objectives use the samples.
    """

    grid: RepGrid
    density: FloatArray
    samples: FloatArray | None = None
    label: str = ""
    meta: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.density = np.asarray(self.density, dtype=float)
        if self.density.shape != self.grid.shape:
            raise ValueError(f"density shape {self.density.shape} != grid shape {self.grid.shape}")
        if np.any(self.density < 0) or not np.all(np.isfinite(self.density)):
            raise ValueError("intensity must be finite and non-negative")
        m = self.grid.mask
        self.density = np.where(m, self.density, 0.0)
        if self.samples is not None:
            s = np.asarray(self.samples, dtype=float)
            if s.ndim != 3 or s.shape[1:] != self.grid.shape or len(s) == 0:
                raise ValueError("samples must have shape (S, n_alpha, n_p)")
            if not np.all(np.isfinite(s)) or np.any(s < 0):
                raise ValueError("samples must be finite and non-negative")
            self.samples = np.where(m[None], s, 0.0)

    @property
    def mass(self) -> FloatArray:
        """Expected number of trajectories per cell."""
        return self.density * self.grid.cell_area

    @property
    def sample_mass(self) -> FloatArray:
        """Per-sample expected counts, shape ``(S, n_alpha, n_p)``.

        Falls back to the point estimate when no samples are stored.
        """
        if self.samples is None:
            return self.mass[None]
        return self.samples * self.grid.cell_area

    def total(self) -> float:
        return float(self.mass.sum())

    def l1(self, other: IntensityField) -> float:
        """``integral |lambda - lambda'|`` over representation space."""
        if other.grid != self.grid:
            raise ValueError("fields live on different grids")
        return float(np.abs(self.mass - other.mass).sum())

    def scaled(self, factor: float) -> IntensityField:
        s = None if self.samples is None else self.samples * factor
        return replace(self, density=self.density * factor, samples=s)

    def with_label(self, label: str) -> IntensityField:
        return replace(self, label=label)

    @staticmethod
    def mixture(fields: list[IntensityField], weights: list[float], label: str = "mixture") -> IntensityField:
        """Convex combination ``sum_k w_k lambda_k`` (weights are normalised).

        This is the ``lambda_E = w_H lambda_H + w_F lambda_F + w_U lambda_U``
        construction from the original extension proposal. Because the
        expected-miss objective is linear in intensity, a mixture whose
        weights are posterior model probabilities is the Bayes-optimal
        input for that objective.
        """
        if len(fields) != len(weights) or not fields:
            raise ValueError("need one weight per field")
        w = np.asarray(weights, dtype=float)
        if not np.all(np.isfinite(w)) or np.any(w < 0) or w.sum() <= 0:
            raise ValueError("weights must be non-negative and not all zero")
        w = w / w.sum()
        g = fields[0].grid
        if any(f.grid != g for f in fields):
            raise ValueError("mixture fields must share a grid")
        dens = sum(wi * f.density for wi, f in zip(w, fields))
        return IntensityField(g, np.asarray(dens), label=label, meta={"weights": w.tolist()})
