"""Estimating trajectory intensity in representation space.

Two estimators are provided:

``kde_intensity``
    Gaussian product-kernel density estimate with exact cell
    integration and Moebius images at the ``alpha = 0 / pi`` seam.
    Bandwidth by Scott's rule or leave-one-out likelihood
    cross-validation.

``lgcp_intensity``
    Log-Gaussian Cox process on the lattice,

        y_c | eta ~ Poisson(A_c * T * exp(eta_c)),
        eta ~ N(m0, Q(theta)^-1),    Q = tau (kappa^2 I + L)^2,

    where ``L`` is the lattice Laplacian with the Moebius seam (a
    discrete Matern/SPDE-type prior, Lindgren et al. 2011). The posterior
    is approximated by a Gaussian at the mode (Laplace approximation) and
    ``theta = (tau, kappa)`` is chosen by maximising the Laplace
    approximation to the marginal likelihood (empirical Bayes). This is
    the same model family as the LGCLP/INLA approach of Kim et al., but
    it is *not* R-INLA: hyperparameters are plugged in rather than
    integrated out.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import scipy.linalg as sla
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.special import ndtr

from ._typing import FloatArray
from .grid import IntensityField, RepGrid

__all__ = [
    "LGCPResult",
    "cv_bandwidth",
    "kde_intensity",
    "lgcp_intensity",
    "scott_bandwidth",
]


def _with_images(
    alpha: FloatArray, p: FloatArray, w: FloatArray
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Add the two Moebius images of every point."""
    a = np.concatenate([alpha, alpha - np.pi, alpha + np.pi])
    pp = np.concatenate([p, -p, -p])
    ww = np.concatenate([w, w, w])
    return a, pp, ww


def scott_bandwidth(alpha: FloatArray, p: FloatArray) -> tuple[float, float]:
    """Scott's rule ``h_d = sigma_d * n^(-1/6)`` for a 2-D product kernel."""
    n = len(alpha)
    if n < 2:
        raise ValueError("need at least two points for a bandwidth")
    f = n ** (-1.0 / 6.0)
    reference = 0.5 * np.angle(np.mean(np.exp(2j * np.asarray(alpha))))
    turns = np.rint((reference - np.asarray(alpha)) / np.pi).astype(int)
    lifted_a = np.asarray(alpha) + turns * np.pi
    lifted_p = np.asarray(p) * np.where(turns % 2 == 0, 1.0, -1.0)
    sa = float(np.std(lifted_a, ddof=1)) or 1e-3
    sp_ = float(np.std(lifted_p, ddof=1)) or 1e-3
    return sa * f, sp_ * f


def _loo_loglik(alpha: FloatArray, p: FloatArray, ha: float, hp: float) -> float:
    a_img, p_img, _ = _with_images(alpha, p, np.ones_like(alpha))
    n = len(alpha)
    za = (alpha[:, None] - a_img[None, :]) / ha
    zp = (p[:, None] - p_img[None, :]) / hp
    k = np.exp(-0.5 * (za**2 + zp**2)) / (2 * np.pi * ha * hp)
    # remove self-contribution (first n columns hold the originals)
    k[np.arange(n), np.arange(n)] = 0.0
    k[np.arange(n), np.arange(n) + n] = 0.0
    k[np.arange(n), np.arange(n) + 2 * n] = 0.0
    f = k.sum(axis=1) / (n - 1)
    return float(np.sum(np.log(np.maximum(f, 1e-300))))


def cv_bandwidth(
    alpha: FloatArray,
    p: FloatArray,
    factors: Sequence[float] = (0.25, 0.35, 0.5, 0.7, 1.0, 1.4, 2.0),
    max_points: int = 1500,
    rng: np.random.Generator | None = None,
) -> tuple[float, float]:
    """Leave-one-out likelihood CV over multiples of Scott's bandwidth.

    The two axes are scaled independently over ``factors x factors``.
    For large samples a random subset of ``max_points`` is used.
    """
    alpha = np.asarray(alpha, dtype=float)
    p = np.asarray(p, dtype=float)
    if len(alpha) > max_points:
        rng = rng or np.random.default_rng(0)
        idx = rng.choice(len(alpha), max_points, replace=False)
        alpha, p = alpha[idx], p[idx]
    ha0, hp0 = scott_bandwidth(alpha, p)
    best = (-np.inf, ha0, hp0)
    for fa in factors:
        for fp in factors:
            ll = _loo_loglik(alpha, p, ha0 * fa, hp0 * fp)
            if ll > best[0]:
                best = (ll, ha0 * fa, hp0 * fp)
    return best[1], best[2]


def _cell_mass_matrix(
    grid: RepGrid,
    alpha: FloatArray,
    p: FloatArray,
    w: FloatArray,
    ha: FloatArray | float,
    hp: FloatArray | float,
) -> FloatArray:
    """Exact Gaussian mass per cell: ``sum_i w_i U_i V_i^T``.

    ``ha`` / ``hp`` may be scalars or per-point arrays.
    """
    ae = grid.alpha_edges
    pe = grid.p_edges
    ha = np.broadcast_to(np.asarray(ha, dtype=float), alpha.shape)
    hp = np.broadcast_to(np.asarray(hp, dtype=float), p.shape)
    ua = ndtr((ae[None, :] - alpha[:, None]) / ha[:, None])
    u = np.diff(ua, axis=1)  # (N, n_alpha)
    vp = ndtr((pe[None, :] - p[:, None]) / hp[:, None])
    v = np.diff(vp, axis=1)  # (N, n_p)
    return (u * w[:, None]).T @ v


def kde_intensity(
    alpha: FloatArray,
    p: FloatArray,
    grid: RepGrid,
    *,
    bandwidth: str | tuple[float, float] = "cv",
    weights: FloatArray | None = None,
    n_epochs: float = 1.0,
    extra_var: tuple[float, float] = (0.0, 0.0),
    label: str = "kde",
) -> IntensityField:
    """Kernel estimate of trajectory intensity per epoch.

    Parameters
    ----------
    alpha, p
        Observed lines in representation space.
    grid
        Target grid.
    bandwidth
        ``"scott"``, ``"cv"`` or an explicit ``(h_alpha, h_p)``.
    weights
        Optional per-line weights (e.g. recency weights).
    n_epochs
        Number of epochs the observations span; the estimate is divided
        by this so it is a per-epoch intensity.
    extra_var
        Additional variance added to the kernel on each axis. Convolving
        the KDE with ``N(0, diag(extra_var))`` gives exactly this, which
        is how predictive (shift) uncertainty is folded in.
    """
    alpha = np.asarray(alpha, dtype=float)
    p = np.asarray(p, dtype=float)
    if alpha.shape != p.shape or alpha.ndim != 1:
        raise ValueError("alpha and p must be 1-D arrays of equal length")
    if not np.all(np.isfinite(alpha)) or not np.all(np.isfinite(p)):
        raise ValueError("line coordinates must be finite")
    if not np.isfinite(n_epochs) or n_epochs <= 0:
        raise ValueError("n_epochs must be finite and positive")
    w = np.ones_like(alpha) if weights is None else np.asarray(weights, dtype=float)
    if w.shape != alpha.shape or not np.all(np.isfinite(w)) or np.any(w < 0):
        raise ValueError("weights must match the lines and be finite and non-negative")
    if len(extra_var) != 2 or not np.all(np.isfinite(extra_var)) or min(extra_var) < 0:
        raise ValueError("extra_var must have two finite non-negative values")
    if len(alpha) == 0:
        return IntensityField(grid, np.zeros(grid.shape), label=label)
    if isinstance(bandwidth, str):
        if len(alpha) < 3:
            ha, hp = 0.05, 0.05 * grid.p_max  # type: ignore[operator]
        elif bandwidth == "scott":
            ha, hp = scott_bandwidth(alpha, p)
        elif bandwidth == "cv":
            ha, hp = cv_bandwidth(alpha, p)
        else:
            raise ValueError(f"unknown bandwidth rule {bandwidth!r}")
    else:
        ha, hp = bandwidth
    if not np.all(np.isfinite([ha, hp])) or min(ha, hp) <= 0:
        raise ValueError("bandwidths must be finite and positive")
    ha_eff = float(np.sqrt(ha**2 + extra_var[0]))
    hp_eff = float(np.sqrt(hp**2 + extra_var[1]))
    a_img, p_img, w_img = _with_images(alpha, p, w)
    mass = _cell_mass_matrix(grid, a_img, p_img, w_img, ha_eff, hp_eff)
    dens = mass / grid.cell_area / n_epochs
    return IntensityField(
        grid,
        dens,
        label=label,
        meta={"bandwidth": (ha, hp), "effective_bandwidth": (ha_eff, hp_eff), "n": len(alpha)},
    )


# ----------------------------------------------------------------------
# LGCP with Laplace approximation
# ----------------------------------------------------------------------


@dataclass
class LGCPResult:
    """Output of :func:`lgcp_intensity`."""

    field: IntensityField
    eta_mode: FloatArray  # posterior mode of log-intensity on masked cells
    eta_var: FloatArray  # marginal posterior variances (Laplace)
    tau: float
    kappa: float
    log_marginal: float  # Laplace approximation at the selected hyperparameters
    hyper_grid: list[tuple[float, float, float]]


def _precision(lap: sp.csr_matrix, tau: float, kappa: float) -> sp.csr_matrix:
    n = lap.shape[0]
    k = sp.identity(n, format="csr") * kappa**2 + lap
    return sp.csr_matrix(tau * (k @ k))


def _laplace_mode(
    y: FloatArray, expo: FloatArray, q: sp.csr_matrix, m0: float, max_iter: int = 60, tol: float = 1e-8
) -> tuple[FloatArray, sp.csr_matrix]:
    """Newton iterations for the posterior mode of ``eta``."""
    eta = np.full_like(y, m0)
    # starting from the empirical log rate speeds convergence
    with np.errstate(divide="ignore"):
        start = np.log((y + 0.5) / expo)
    eta = 0.5 * eta + 0.5 * start
    for _ in range(max_iter):
        mu = expo * np.exp(eta)
        grad = y - mu - q @ (eta - m0)
        h = q + sp.diags(mu)
        step = spla.spsolve(sp.csc_matrix(h), grad)
        # damped step for robustness
        t = 1.0
        f_old = _log_post(y, expo, q, m0, eta)
        while t > 1e-4:
            cand = eta + t * step
            if _log_post(y, expo, q, m0, cand) >= f_old - 1e-10:
                break
            t *= 0.5
        eta = eta + t * step
        if np.max(np.abs(t * step)) < tol:
            break
    mu = expo * np.exp(eta)
    return eta, sp.csr_matrix(q + sp.diags(mu))


def _log_post(y: FloatArray, expo: FloatArray, q: sp.csr_matrix, m0: float, eta: FloatArray) -> float:
    d = eta - m0
    return float(np.sum(y * eta - expo * np.exp(eta)) - 0.5 * d @ (q @ d))


def _logdet_spd(a: sp.csr_matrix) -> float:
    lu = spla.splu(sp.csc_matrix(a), permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.0)
    return float(np.sum(np.log(np.abs(lu.U.diagonal()))))


def lgcp_intensity(
    alpha: FloatArray,
    p: FloatArray,
    grid: RepGrid,
    *,
    n_epochs: float = 1.0,
    sigmas: Sequence[float] = (0.5, 1.0, 2.0),
    ranges: Sequence[float] = (4.0, 8.0, 16.0),
    n_samples: int = 64,
    rng: np.random.Generator | None = None,
    max_dense: int = 4000,
    fit_shape: tuple[int, int] | None = None,
    label: str = "lgcp",
) -> LGCPResult:
    """Fit an LGCP to observed lines and return posterior intensity.

    The returned field's ``density`` is the posterior mean
    ``E[exp(eta)] = exp(eta_hat + var/2)`` and ``samples`` are draws
    from the Gaussian (Laplace) posterior. Only cells inside
    ``grid.mask`` are modelled.

    Note: traffic lanes are sharply concentrated, so the log intensity
    varies over several orders of magnitude and the marginal likelihood
    favours a large prior variance. In cells far from any data the
    lognormal posterior mean then sits well above the posterior median,
    and the posterior-mean total can exceed the observed count (by tens
    of percent for ~100 lines). This is a property of the stationary
    prior, not a numerical error; ``eta_mode`` gives the median.

    Parameters
    ----------
    sigmas, ranges
        Hyperparameter grid for empirical Bayes selection: prior marginal
        standard deviation of ``eta`` and correlation range in cells. They
        map to the precision parameters by the lattice Matern relations
        ``kappa = sqrt(8) / range`` and ``tau = 1 / (4 pi kappa^2 sigma^2)``.
        The default caps ``sigma`` at 2 as a weakly informative prior
        choice: the marginal likelihood keeps asking for larger values on
        lane-like data, which inflates the posterior mean in empty cells.
    n_samples
        Number of posterior intensity draws to keep.
    max_dense
        Posterior sampling uses a dense Cholesky factor, so the number of
        masked cells must not exceed this.
    fit_shape
        Optional coarser ``(n_alpha, n_p)`` lattice for the fit. The
        posterior mean and samples are interpolated back onto ``grid``
        (mass preserving). ``eta_mode`` / ``eta_var`` refer to the fit
        lattice.
    """
    rng = rng or np.random.default_rng(0)
    out_grid: RepGrid | None = None
    if fit_shape is not None and tuple(fit_shape) != grid.shape:
        out_grid = grid
        grid = RepGrid(grid.window, fit_shape[0], fit_shape[1], grid.margin, grid.p_max)
    alpha = np.asarray(alpha, dtype=float)
    p = np.asarray(p, dtype=float)
    mask = grid.mask.ravel()
    n_cells = int(mask.sum())
    if n_cells > max_dense:
        raise ValueError(f"{n_cells} active cells exceeds max_dense={max_dense}; use a coarser grid")
    y_full = grid.histogram(alpha, p).ravel()
    y = y_full[mask]
    expo = np.full(n_cells, grid.cell_area * n_epochs)
    lap_full = grid.laplacian()
    idx = np.flatnonzero(mask)
    lap_sub = lap_full[idx][:, idx]
    # restricted Laplacian: rebuild degrees on the subgraph
    adj = -(lap_sub - sp.diags(lap_sub.diagonal()))
    lap = sp.csr_matrix(sp.diags(np.asarray(adj.sum(axis=1)).ravel()) - adj)
    total_area = n_cells * grid.cell_area * n_epochs
    m0 = float(np.log(max(y.sum(), 0.5) / total_area))

    best: tuple[float, float, float, FloatArray, sp.csr_matrix] | None = None
    hyper: list[tuple[float, float, float]] = []
    for sigma in sigmas:
        for rng_cells in ranges:
            kappa = float(np.sqrt(8.0) / rng_cells)
            tau = float(1.0 / (4 * np.pi * kappa**2 * sigma**2))
            q = _precision(lap, tau, kappa)
            eta, h = _laplace_mode(y, expo, q, m0)
            d = eta - m0
            lml = (
                float(np.sum(y * np.log(expo) + y * eta - expo * np.exp(eta)))
                - 0.5 * float(d @ (q @ d))
                + 0.5 * _logdet_spd(q)
                - 0.5 * _logdet_spd(h)
            )
            hyper.append((tau, kappa, lml))
            if best is None or lml > best[0]:
                best = (lml, tau, kappa, eta, h)
    assert best is not None
    lml, tau, kappa, eta, h = best

    hd = h.toarray()
    chol = sla.cholesky(hd, lower=True)
    # marginal variances diag(H^-1) via the inverse of the Cholesky factor
    linv = sla.solve_triangular(chol, np.eye(n_cells), lower=True)
    var = np.sum(linv**2, axis=0)
    z = rng.standard_normal((n_cells, n_samples))
    draws = eta[:, None] + sla.solve_triangular(chol.T, z, lower=False)

    def to_grid(vec: FloatArray) -> FloatArray:
        out = np.zeros(grid.n_alpha * grid.n_p)
        out[mask] = vec
        return out.reshape(grid.shape)

    mean = to_grid(np.exp(eta + 0.5 * var))
    samples = np.stack([to_grid(np.exp(draws[:, s])) for s in range(n_samples)])
    if out_grid is not None and out_grid != grid:
        mean = _resample(grid, out_grid, mean)
        samples = np.stack([_resample(grid, out_grid, s) for s in samples])
        grid = out_grid
    field = IntensityField(
        grid,
        mean,
        samples=samples,
        label=label,
        meta={"tau": tau, "kappa": kappa, "log_marginal": lml, "n": len(alpha)},
    )
    return LGCPResult(field, eta, var, tau, kappa, lml, hyper)


def _resample(src: RepGrid, dst: RepGrid, dens: FloatArray) -> FloatArray:
    """Move a density between grids by bilinear interpolation, keeping total mass."""
    from scipy.interpolate import RegularGridInterpolator

    total = float(dens.sum() * src.cell_area)
    interp = RegularGridInterpolator(
        (src.alpha, src.p), dens, method="linear", bounds_error=False, fill_value=None
    )
    a, pp = dst.mesh()
    out = np.maximum(interp(np.column_stack([a.ravel(), pp.ravel()])).reshape(dst.shape), 0.0)
    out = np.where(dst.mask, out, 0.0)
    s = float(out.sum() * dst.cell_area)
    return out * (total / s) if s > 0 else out
