"""Checks of proposed research machinery, independent of performance outcomes."""

from pathlib import Path

import numpy as np
import pytest

from stochplace import make_scenario


@pytest.mark.parametrize(
    "name", ["accelerating", "rotating_quadratic", "random_walk", "random_switch", "lane_split"]
)
def test_new_motion_is_reproducible_and_samples_hit_window(name):
    first = make_scenario(name, scenario_seed=3)
    second = make_scenario(name, scenario_seed=3)
    np.testing.assert_allclose([ln.centre(9) for ln in first.lanes], [ln.centre(9) for ln in second.lanes])
    a, p = first.sample(9, np.random.default_rng(5), n=100)
    assert first.window.line_hits(a, p).all()
    assert len(a) > 0


def test_acceleration_and_split_are_not_constant_velocity():
    lane = make_scenario("accelerating").lanes[0]
    p = np.array([lane.centre(t)[1] for t in range(3)])
    assert np.diff(p, n=2)[0] == pytest.approx(0.06)
    split = make_scenario("lane_split")
    assert split.lanes[0].centre(5) == split.lanes[1].centre(5)
    assert split.lanes[1].centre(9)[1] - split.lanes[0].centre(9)[1] == pytest.approx(5.2)


def test_random_walk_uses_an_independent_scenario_seed():
    a = make_scenario("random_walk", scenario_seed=3).lanes[0]
    b = make_scenario("random_walk", scenario_seed=4).lanes[0]
    assert a.centre(9) != b.centre(9)


def test_latent_loss_rank_handles_ties_and_out_of_range_truth():
    from stochplace.experiment import sample_diagnostics

    result = sample_diagnostics(np.array([1.0, 2.0, 3.0]), 2.0)
    assert result["sample_rank"] == pytest.approx(0.5)
    assert result["sample_covered_90"]
    assert result["sample_low"] == pytest.approx(1.1)
    assert result["sample_high"] == pytest.approx(2.9)
    result = sample_diagnostics(np.array([1.0, 2.0, 3.0]), 4.0)
    assert result["sample_rank"] == 1.0
    assert not result["sample_covered_90"]
    with pytest.raises(ValueError):
        sample_diagnostics(np.array([]), 1.0)


def test_weighted_candidate_keeps_point_field_and_resamples_only_available_draws(monkeypatch, small_grid):
    from scripts.research_samplers import fm, weighted_candidate

    from stochplace import ForecastConfig, IntensityField

    density = np.ones(small_grid.shape)
    first = IntensityField(small_grid, density)
    second = IntensityField(small_grid, 3 * density, samples=np.stack([2 * density, 4 * density]))
    current = IntensityField(small_grid, 2.5 * density, meta={"weights": {"pooled": 0.25, "recent": 0.75}})
    monkeypatch.setitem(fm.FORECASTERS, "pooled", lambda *args: first)
    monkeypatch.setitem(fm.FORECASTERS, "recent", lambda *args: second)
    config = ForecastConfig(stack_models=("pooled", "recent"), n_samples=8, bandwidth=(0.1, 0.4))
    a = weighted_candidate([(np.array([1.0]), np.array([0.0]))], small_grid, 1, config, current, 5)
    b = weighted_candidate([(np.array([1.0]), np.array([0.0]))], small_grid, 1, config, current, 5)
    np.testing.assert_array_equal(a.density, current.density)
    np.testing.assert_array_equal(a.samples, b.samples)
    assert np.isin(a.samples[:, small_grid.mask], [1.75, 3.25]).all()


def test_relative_floor_stacking_gradient_is_independent_finite_difference():
    from scripts.ais_research import intensity_loss

    design = np.array([[1.0, 0.1], [0.2, 3.0], [2.0, 1.0]])
    totals, weights = np.array([3.0, 4.0]), np.array([0.4, 0.6])
    _, analytic = intensity_loss(weights, design, totals)
    numerical = []
    for i in range(len(weights)):
        plus, minus = weights.copy(), weights.copy()
        plus[i] += 1e-6
        minus[i] -= 1e-6
        numerical.append(
            (intensity_loss(plus, design, totals)[0] - intensity_loss(minus, design, totals)[0]) / 2e-6
        )
    np.testing.assert_allclose(analytic, numerical, rtol=1e-5, atol=1e-8)


def test_minimum_origin_policy_uses_pooled_before_three_backtests(small_grid):
    from scripts.ais_research import policy_forecast

    from stochplace import ForecastConfig, forecast

    history = make_scenario("stationary").history(4, np.random.default_rng(4))
    config = ForecastConfig(n_samples=3, bandwidth=(0.1, 0.4))
    proposed = policy_forecast(history, small_grid, "stacked", config, policy="minimum_origins")
    pooled = forecast(history, small_grid, 1, "pooled", config)
    np.testing.assert_array_equal(proposed.density, pooled.density)
    assert proposed.meta["backtest_origins"] == 1
    assert proposed.meta["weight_fit"] == "minimum_origins_pooled"


@pytest.mark.parametrize("radius", [0.0, 0.2, 2.0])
def test_transport_dual_agrees_with_independent_primal_lp(radius):
    from scipy.optimize import linprog
    from scripts.transport_objective import line_cost, transport_bound

    from stochplace import Window

    alpha = np.array([0.05, 0.5, 1.2, 2.3])
    offsets = np.array([-0.2, 0.6, -0.4, 0.1])
    cost = line_cost(alpha, offsets, Window(-2, 2, -1, 1))
    mass, loss = np.array([0.1, 0.2, 0.3, 0.4]), np.array([0.3, 0.9, 0.2, 0.6])
    constraints = np.zeros((4, 16))
    for row in range(4):
        constraints[row, 4 * row : 4 * (row + 1)] = 1
    result = linprog(
        -np.tile(loss, 4),
        A_eq=constraints,
        b_eq=mass,
        A_ub=cost.ravel()[None],
        b_ub=[radius],
        bounds=(0, None),
        method="highs",
    )
    assert result.success
    bound = transport_bound(mass, loss, cost, radius)
    assert bound >= -result.fun - 1e-10
    assert bound == pytest.approx(-result.fun, abs=1e-8)


def test_line_metric_respects_seam_and_transport_identity():
    from scripts.transport_objective import line_cost, transport_distance

    from stochplace import Window

    alpha, offsets = np.array([0.1, 0.7, 1.8]), np.array([-0.5, 0.2, 0.8])
    cost = line_cost(alpha, offsets, Window(-2, 2, -1, 1))
    flipped = line_cost(alpha + np.pi, -offsets, Window(-2, 2, -1, 1))
    np.testing.assert_allclose(cost, flipped, rtol=0, atol=1e-12)
    for middle in range(3):
        assert (cost <= cost[:, middle, None] + cost[None, middle, :] + 1e-12).all()
    mass = np.array([0.2, 0.3, 0.5])
    assert transport_distance(mass, mass, cost) == pytest.approx(0, abs=1e-12)


def test_concentrated_transport_masses_remain_feasible():
    from scripts.transport_objective import transport_distance

    data = np.load(Path(__file__).parent / "fixtures" / "concentrated_transport.npz")
    first, second, cost = data["first"], data["second"], data["cost"]
    value = transport_distance(first, second, cost)
    independent_coupling = first[:, None] * second[None, :]
    assert 0 <= value <= float(np.sum(independent_coupling * cost)) + 1e-9
