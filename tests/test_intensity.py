import numpy as np
import pytest

from stochplace import IntensityField, Lane, RepGrid, Scenario, kde_intensity, lgcp_intensity
from stochplace.intensity import cv_bandwidth, scott_bandwidth


def _central_points(rng, n):
    return rng.normal(1.6, 0.08, n), rng.normal(0.0, 0.6, n)


def test_kde_mass_per_epoch(grid, rng):
    a, p = _central_points(rng, 400)
    f = kde_intensity(a, p, grid, bandwidth="scott", n_epochs=4)
    assert np.isclose(f.total(), 100, rtol=0.02)


def test_kde_extra_var_equals_wider_kernel(grid, rng):
    a, p = _central_points(rng, 200)
    f1 = kde_intensity(a, p, grid, bandwidth=(0.05, 0.3), extra_var=(0.03**2, 0.4**2))
    f2 = kde_intensity(a, p, grid, bandwidth=(np.hypot(0.05, 0.03), np.hypot(0.3, 0.4)))
    np.testing.assert_allclose(f1.density, f2.density, rtol=1e-10, atol=1e-12)


def test_kde_moebius_image(window):
    g = RepGrid(window, 90, 48)
    f = kde_intensity(np.array([0.01]), np.array([3.0]), g, bandwidth=(0.05, 0.3))
    ia, jp = g.locate(np.array([np.pi - 0.03]), np.array([-3.0]))
    # mass leaks across the seam to (pi - eps, -p)
    assert f.density[ia[0], jp[0]] > 0.1 * f.density.max()


def test_bandwidth_rules(rng):
    a = np.concatenate([rng.normal(1.0, 0.03, 200), rng.normal(2.0, 0.03, 200)])
    p = np.concatenate([rng.normal(-2, 0.2, 200), rng.normal(2, 0.2, 200)])
    hs = scott_bandwidth(a, p)
    hc = cv_bandwidth(a, p)
    # Scott oversmooths a bimodal sample; CV must not pick wider kernels
    assert hc[0] <= hs[0] and hc[1] <= hs[1]
    with pytest.raises(ValueError):
        scott_bandwidth(np.array([1.0]), np.array([1.0]))


def test_kde_empty_and_errors(grid):
    f = kde_intensity(np.array([]), np.array([]), grid)
    assert f.total() == 0
    with pytest.raises(ValueError):
        kde_intensity(np.zeros(3), np.zeros(2), grid)
    with pytest.raises(ValueError):
        kde_intensity(np.zeros(5), np.zeros(5), grid, bandwidth="nope")


def _lane_truth(window):
    lane = Lane(1.7, 0.0, 0.08, 1.0)
    return Scenario("t", [lane], window, rate=1.0)


@pytest.mark.slow
def test_lgcp_recovers_intensity(window):
    g = RepGrid(window, 60, 32)
    sc = _lane_truth(window)
    truth = sc.truth(g, 0)
    errs = []
    for n in (100, 1600):
        rng = np.random.default_rng(n)
        a, p = sc.sample(0, rng, n=n)
        res = lgcp_intensity(a, p, g, n_epochs=1, n_samples=32, rng=rng)
        f = res.field
        errs.append(f.l1(truth.scaled(len(a))) / len(a))
        # posterior mean total approaches the observed count as data grows
        # (lognormal tails inflate it when data are sparse; see docstring)
        tol = 0.6 if n == 100 else 0.1
        assert abs(f.total() - len(a)) / len(a) < tol
        median_total = np.exp(res.eta_mode).sum() * g.cell_area
        assert abs(median_total - len(a)) / len(a) < 0.1
        # the stored mean agrees with the sample mean
        assert np.allclose(f.samples.mean(axis=0).sum(), f.density.sum(), rtol=0.25)
    assert errs[1] < errs[0]
    assert errs[1] < 0.25


def test_lgcp_mode_is_stationary(window):
    """At the returned mode the gradient of the log posterior is ~0."""
    from stochplace.intensity import _laplace_mode, _precision

    g = RepGrid(window, 24, 16)
    sc = _lane_truth(window)
    rng = np.random.default_rng(3)
    a, p = sc.sample(0, rng, n=300)
    y = g.histogram(a, p).ravel()
    lap = g.laplacian()
    q = _precision(lap, 0.5, 0.3)
    expo = np.full(y.size, g.cell_area)
    m0 = float(np.log(y.sum() / (y.size * g.cell_area)))
    eta, _ = _laplace_mode(y, expo, q, m0)
    grad = y - expo * np.exp(eta) - q @ (eta - m0)
    assert np.max(np.abs(grad)) < 1e-6


def test_lgcp_coarse_fit_preserves_mass(grid):
    sc = _lane_truth(grid.window)
    rng = np.random.default_rng(5)
    a, p = sc.sample(0, rng, n=500)
    res = lgcp_intensity(a, p, grid, fit_shape=(45, 24), n_samples=8, rng=rng)
    assert res.field.grid == grid
    assert res.field.samples.shape == (8, *grid.shape)
    assert abs(res.field.total() - 500) / 500 < 0.3


def test_lgcp_too_large(window):
    g = RepGrid(window, 200, 100)
    with pytest.raises(ValueError):
        lgcp_intensity(np.array([1.0]), np.array([0.0]), g, max_dense=100)


def test_field_scaled(grid):
    f = IntensityField(grid, np.ones(grid.shape), samples=np.ones((2, *grid.shape)))
    s = f.scaled(2.0)
    assert np.isclose(s.total(), 2 * f.total())
    assert np.allclose(s.samples, 2 * f.samples)
