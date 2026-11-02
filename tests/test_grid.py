import numpy as np
import pytest

from stochplace import IntensityField, RepGrid, Window


def test_laplacian_properties(small_grid):
    lap = small_grid.laplacian()
    d = lap.toarray()
    assert np.allclose(d, d.T)
    assert np.allclose(d.sum(axis=1), 0)
    assert np.all(np.linalg.eigvalsh(d) > -1e-9)


def test_moebius_seam(small_grid):
    lap = small_grid.laplacian().toarray()
    na, npp = small_grid.shape
    idx = np.arange(na * npp).reshape(na, npp)
    for j in range(npp):
        assert lap[idx[0, j], idx[na - 1, npp - 1 - j]] == -1
        if j != npp - 1 - j:
            assert lap[idx[0, j], idx[na - 1, j]] == 0


def test_histogram_and_locate(small_grid):
    rng = np.random.default_rng(0)
    a = rng.uniform(0, np.pi, 500)
    p = rng.uniform(-small_grid.p_max, small_grid.p_max, 500)
    h = small_grid.histogram(a, p)
    assert h.sum() == 500
    # out-of-range p is dropped
    h2 = small_grid.histogram(np.array([1.0]), np.array([small_grid.p_max + 1]))
    assert h2.sum() == 0


def test_mask_matches_window_hits(small_grid):
    a, pp = small_grid.mesh()
    np.testing.assert_array_equal(small_grid.mask, small_grid.window.line_hits(a, pp))


def test_field_validation(small_grid):
    with pytest.raises(ValueError):
        IntensityField(small_grid, -np.ones(small_grid.shape))
    with pytest.raises(ValueError):
        IntensityField(small_grid, np.ones((3, 3)))
    f = IntensityField(small_grid, np.ones(small_grid.shape))
    assert np.all(f.density[~small_grid.mask] == 0)
    assert np.isclose(f.total(), small_grid.mask.sum() * small_grid.cell_area)


def test_mixture_and_l1(small_grid):
    f1 = IntensityField(small_grid, np.ones(small_grid.shape))
    f2 = IntensityField(small_grid, 3 * np.ones(small_grid.shape))
    m = IntensityField.mixture([f1, f2], [1, 1])
    assert np.allclose(m.density[small_grid.mask], 2)
    assert np.isclose(f1.l1(f2), f2.l1(f1))
    assert np.isclose(f1.l1(f2), 2 * f1.total())
    with pytest.raises(ValueError):
        IntensityField.mixture([f1], [-1])
    other = IntensityField(RepGrid(Window(-1, 1, -1, 1), 8, 8), np.ones((8, 8)))
    with pytest.raises(ValueError):
        f1.l1(other)
