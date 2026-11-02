import numpy as np
import pytest

from stochplace import FORECASTERS, ForecastConfig, IntensityField, RepGrid, forecast, make_scenario
from stochplace.forecast import _fit_drift, backtest_log_scores, poisson_log_score
from stochplace.scenarios import SCENARIOS


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_truth_total_and_sampling(name, grid):
    sc = make_scenario(name)
    rng = np.random.default_rng(0)
    for t in (0.0, 5.0):
        truth = sc.truth(grid, t)
        # truth is per epoch; lanes are inside the window up to boundary effects
        counts = [len(sc.sample(t, rng)[0]) for _ in range(300)]
        assert abs(np.mean(counts) - truth.total()) < 0.05 * truth.total() + 3


def test_samples_follow_truth(grid):
    sc = make_scenario("lane_shift")
    rng = np.random.default_rng(1)
    a, p = sc.sample(2.0, rng, n=200_000)
    h = grid.histogram(a, p) / len(a)
    t = sc.truth(grid, 2.0)
    l1 = np.abs(h - t.mass / t.mass.sum()).sum()
    assert l1 < 0.05


def test_weights_shift_over_time():
    sc = make_scenario("lane_shift")
    assert sc.weights(0)[0] > 0.9
    assert sc.weights(10)[1] > 0.9
    assert np.isclose(sc.weights(3).sum(), 1)
    with pytest.raises(KeyError):
        make_scenario("tornado")


def test_drift_velocity_recovered():
    sc = make_scenario("drift", speed=0.3)
    rng = np.random.default_rng(2)
    hist = [sc.sample(t, rng, n=2000) for t in range(8)]
    fit = _fit_drift(hist)
    lane = sc.lanes[0]
    assert abs(fit.v[1] - lane.v_p) < 0.05
    assert abs(fit.v[0] - lane.v_alpha) < 0.01


@pytest.mark.parametrize("method", sorted(FORECASTERS))
def test_forecasters_produce_valid_fields(method, grid):
    sc = make_scenario("drift", speed=0.25)
    rng = np.random.default_rng(3)
    hist = sc.history(6, rng)
    cfg = ForecastConfig(n_samples=6, backtest_epochs=2)
    f = forecast(hist, grid, 2, method, cfg)
    mean_count = np.mean([len(a) for a, _ in hist])
    assert np.all(np.isfinite(f.density))
    assert abs(f.total() - mean_count) / mean_count < 0.25
    if f.samples is not None:
        assert f.samples.shape[1:] == grid.shape


def test_forecast_errors(grid):
    with pytest.raises(KeyError):
        forecast([(np.zeros(3), np.zeros(3))], grid, 1, "crystal_ball")
    with pytest.raises(ValueError):
        forecast([], grid, 1, "pooled")


def test_drift_beats_pooled_under_drift(grid):
    sc = make_scenario("drift", speed=0.4)
    rng = np.random.default_rng(4)
    hist = sc.history(8, rng)
    truth = sc.truth(grid, 9)
    cfg = ForecastConfig()
    e_pool = forecast(hist, grid, 2, "pooled", cfg).l1(truth)
    e_drift = forecast(hist, grid, 2, "drift", cfg).l1(truth)
    assert e_drift < 0.5 * e_pool


def test_drift_uncertainty_is_calibrated_without_drift():
    """With no drift, v_hat / sd(v_hat) behaves like a unit-variance score."""
    sc = make_scenario("stationary")
    z = []
    for s in range(150):
        fit = _fit_drift(sc.history(8, np.random.default_rng(s)))
        z.append(fit.v / np.sqrt(fit.v_var))
    z = np.array(z)
    assert np.all(np.abs(z.mean(axis=0)) < 0.3)
    assert np.all((z.std(axis=0) > 0.7) & (z.std(axis=0) < 1.3))


def test_log_score_prefers_truth(grid):
    sc = make_scenario("lane_shift")
    rng = np.random.default_rng(6)
    a, p = sc.sample(1.0, rng)
    right = sc.truth(grid, 1.0)
    wrong = sc.truth(grid, 12.0)
    assert poisson_log_score(right, a, p) > poisson_log_score(wrong, a, p)


def test_stacking_weights_favour_correct_model(grid):
    sc = make_scenario("drift", speed=0.5)
    rng = np.random.default_rng(7)
    hist = sc.history(8, rng)
    cfg = ForecastConfig(n_samples=4)
    f = forecast(hist, grid, 2, "stacked", cfg)
    w = f.meta["weights"]
    assert np.isclose(sum(w.values()), 1)
    assert w["drift_u"] + w["trend"] > w["pooled"]
    scores = backtest_log_scores(hist, grid, 2, ("pooled", "drift"), cfg, (0.03, 0.4))
    assert scores["drift"] > scores["pooled"]


def test_mixture_is_convex_combination(grid):
    sc = make_scenario("drift")
    rng = np.random.default_rng(8)
    hist = sc.history(6, rng)
    cfg = ForecastConfig(n_samples=4, mixture_weights=(1.0, 0.0, 0.0))
    bw = (0.03, 0.4)
    m = forecast(hist, grid, 2, "mixture", cfg, bw)
    p = forecast(hist, grid, 2, "pooled", cfg, bw)
    np.testing.assert_allclose(m.density, p.density)
    assert isinstance(m, IntensityField)


def test_rep_grid_is_shared(grid):
    sc = make_scenario("emergence")
    rng = np.random.default_rng(9)
    hist = sc.history(5, rng)
    fields = [
        forecast(hist, grid, 1, m, ForecastConfig(n_samples=3, backtest_epochs=1))
        for m in ("pooled", "trend")
    ]
    assert all(f.grid == grid for f in fields)
    assert isinstance(grid, RepGrid)
