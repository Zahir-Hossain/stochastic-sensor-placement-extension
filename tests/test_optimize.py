import numpy as np
import pytest

from stochplace import (
    DiskSensor,
    IntensityField,
    Problem,
    Window,
    brute_force,
    fence_placement,
    greedy,
    make_scenario,
    random_placement,
    refine,
    solve,
)


@pytest.mark.parametrize("seed", range(6))
def test_greedy_approximation_bound(small_grid, sensor, seed):
    """Greedy detected mass >= (1 - 1/e) * optimum over the candidate set."""
    rng = np.random.default_rng(seed)
    f = IntensityField(small_grid, rng.gamma(0.6, 1.0, small_grid.shape))
    prob = Problem(f, sensor)
    cand = small_grid.window.grid(1.0)  # 9 x 5 = 45 candidates
    k = 3
    g = greedy(prob, cand, k)
    b = brute_force(prob, cand, k)
    total = f.total()
    F_g, F_b = total - g.value, total - b.value
    assert F_b >= F_g - 1e-9
    assert F_g >= (1 - 1 / np.e) * F_b


def test_greedy_history_decreases(small_grid, sensor):
    rng = np.random.default_rng(0)
    f = IntensityField(small_grid, rng.gamma(2.0, 1.0, small_grid.shape))
    g = greedy(Problem(f, sensor), small_grid.window.grid(1.0), 4)
    assert all(np.diff(g.history) <= 1e-12)
    assert len(set(g.meta["indices"])) == 4


def test_greedy_validation(small_grid, sensor):
    f = IntensityField(small_grid, np.ones(small_grid.shape))
    with pytest.raises(ValueError):
        greedy(Problem(f, sensor), np.zeros((2, 2)), 3)


def test_refine_improves_and_respects_bounds(window, sensor):
    sc = make_scenario("lane_shift")
    from stochplace import RepGrid

    g = RepGrid(window, 90, 48)
    f = sc.truth(g, 3)
    prob = Problem(f, sensor)
    cand = window.grid(2.5)
    start = greedy(prob, cand, 4)
    ref = refine(prob, start, window)
    assert ref.value <= start.value + 1e-12
    assert window.contains(ref.sensors).all()
    # disk sensors are not refined
    pd = Problem(f, DiskSensor())
    st = greedy(pd, cand, 2)
    assert refine(pd, st, window) is st


def test_robust_solve_runs(small_grid, sensor):
    rng = np.random.default_rng(4)
    samples = rng.gamma(1.0, 1.0, (12, *small_grid.shape))
    f = IntensityField(small_grid, samples.mean(axis=0), samples=samples)
    for obj in ("void", "cvar"):
        pl = solve(Problem(f, sensor, obj), small_grid.window.grid(1.0), 3, small_grid.window)
        assert pl.sensors.shape == (3, 2)
        assert np.isfinite(pl.value)


def test_baselines(small_grid, sensor):
    f = IntensityField(small_grid, np.ones(small_grid.shape))
    prob = Problem(f, sensor)
    w = small_grid.window
    fp = fence_placement(prob, w, 4)
    assert np.allclose(fp.sensors[:, 1], 0.0)
    assert np.all(np.diff(fp.sensors[:, 0]) > 0)
    tall = Window(-1, 1, -5, 5)
    assert np.allclose(fence_placement(prob, tall, 3).sensors[:, 0], 0.0)
    rp = random_placement(prob, w, 5, np.random.default_rng(0))
    assert w.contains(rp.sensors).all()


def test_brute_force_limit(small_grid, sensor):
    f = IntensityField(small_grid, np.ones(small_grid.shape))
    with pytest.raises(ValueError):
        brute_force(Problem(f, sensor), small_grid.window.grid(0.25), 4, max_subsets=10)
