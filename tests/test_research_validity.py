"""Independent checks for validation leakage, tail risk and robust planning."""

from __future__ import annotations

from importlib import import_module

import numpy as np
import pytest
from scipy.optimize import linprog

from stochplace import (
    ForecastConfig,
    GaussianSensor,
    IntensityField,
    Problem,
    RepGrid,
    Window,
    brute_force,
    cvar_weights,
    forecast,
    greedy,
    make_scenario,
    solve,
    tv_adversary,
    tv_values,
)

fm = import_module("stochplace.forecast")


@pytest.mark.parametrize("method", ["stacked", "pseudo_bma"])
def test_ensemble_refits_bandwidth_inside_each_training_prefix(monkeypatch, small_grid, method):
    history = make_scenario("drift").history(8, np.random.default_rng(1))
    fitted_lengths = []

    def record_bandwidth(prefix, cfg):
        fitted_lengths.append(len(prefix))
        return (0.04, 0.4)

    monkeypatch.setattr(fm, "_bandwidth", record_bandwidth)
    forecast(history, small_grid, 2, method, ForecastConfig(n_samples=3), bw=(0.04, 0.4))
    assert fitted_lengths == [4, 5, 6]  # targets 5,6,7; lead two


def test_intensity_stacking_learns_a_complementary_combination(monkeypatch, small_grid):
    active = np.argwhere(small_grid.mask)
    i, j = active[len(active) // 3], active[2 * len(active) // 3]
    a = np.array([small_grid.alpha[i[0]]] * 8 + [small_grid.alpha[j[0]]] * 2)
    p = np.array([small_grid.p[i[1]]] * 8 + [small_grid.p[j[1]]] * 2)
    history = [(a, p)] * 6
    d1, d2 = np.zeros(small_grid.shape), np.zeros(small_grid.shape)
    d1[tuple(i)], d2[tuple(j)] = 10 / small_grid.cell_area, 10 / small_grid.cell_area
    monkeypatch.setitem(fm.FORECASTERS, "pooled", lambda *args: IntensityField(small_grid, d1))
    monkeypatch.setitem(fm.FORECASTERS, "recent", lambda *args: IntensityField(small_grid, d2))
    cfg = ForecastConfig(stack_models=("pooled", "recent"), n_samples=4, bandwidth=(0.1, 0.4))
    combined = forecast(history, small_grid, 1, "stacked", cfg)
    selected = forecast(history, small_grid, 1, "pseudo_bma", cfg)
    assert combined.meta["weights"]["pooled"] == pytest.approx(0.8, abs=1e-5)
    assert selected.meta["weights"]["pooled"] > 0.999
    assert fm.poisson_log_score(combined, a, p) > fm.poisson_log_score(selected, a, p)


@pytest.mark.parametrize("n,beta", [(32, 0.9), (7, 0.75), (5, 0.0), (9, 0.99)])
def test_cvar_matches_independent_epigraph_linear_program(n, beta):
    losses = np.random.default_rng(n).uniform(0, 15, n)
    # min eta + sum(u_i)/(n*(1-beta)), u_i >= loss_i-eta, u_i >=0
    objective = np.r_[1.0, np.full(n, 1 / (n * (1 - beta)))]
    constraints = np.column_stack([-np.ones(n), -np.eye(n)])
    result = linprog(
        objective, A_ub=constraints, b_ub=-losses, bounds=[(None, None)] + [(0, None)] * n, method="highs"
    )
    assert result.success
    assert cvar_weights(losses, beta) @ losses == pytest.approx(result.fun, abs=1e-9)


def test_fractional_cvar_boundary():
    losses = np.arange(32.0)
    weights = cvar_weights(losses, 0.9)
    assert weights.sum() == pytest.approx(1.0)
    assert weights @ losses == pytest.approx(29.875)
    assert weights[28] == pytest.approx(0.2 / 3.2)


@pytest.mark.parametrize("radius", [0.0, 0.03, 0.25, 0.8, 1.0])
def test_tv_adversary_matches_an_independent_linear_program(radius):
    rng = np.random.default_rng(12)
    n = 8
    m, q = rng.dirichlet(np.ones(n)) * 13, rng.uniform(0, 1, n)
    # variables: adversarial masses x, absolute deviations z
    identity = np.eye(n)
    a = np.vstack(
        [
            np.column_stack([identity, -identity]),
            np.column_stack([-identity, -identity]),
            np.r_[np.zeros(n), np.ones(n)][None],
        ]
    )
    b = np.r_[m, -m, 2 * radius * m.sum()]
    result = linprog(
        np.r_[-q, np.zeros(n)],
        A_ub=a,
        b_ub=b,
        A_eq=np.r_[np.ones(n), np.zeros(n)][None],
        b_eq=[m.sum()],
        bounds=[(0, None)] * (2 * n),
        method="highs",
    )
    assert result.success
    worst = tv_adversary(m, q, radius)
    assert worst.value == pytest.approx(-result.fun, abs=1e-9)
    assert worst.mass.sum() == pytest.approx(m.sum())
    assert worst.mass.min() >= -1e-12
    assert 0.5 * np.abs(worst.mass - m).sum() <= radius * m.sum() + 1e-9
    assert tv_values(m, q, radius) == pytest.approx(worst.value)


def test_tv_vectorisation_ties_and_zero_mass():
    m = np.array([1.0, 2.0, 3.0])
    q = np.array([[0.0, 0.5, 1.0], [0.2, 0.2, 0.2]])
    np.testing.assert_allclose(tv_values(m, q, 0.2), [tv_adversary(m, x, 0.2).value for x in q])
    assert tv_adversary(m, q[1], 1.0).moved_mass == 0
    assert tv_adversary(np.zeros(3), q[0], 0.5).value == 0


def test_tv_solver_against_enumeration(small_grid):
    field = make_scenario("stationary").truth(small_grid, 0)
    problem = Problem(field, GaussianSensor(), "tv", radius=0.15)
    candidates = small_grid.window.grid(2.0)
    g = greedy(problem, candidates, 2)
    improved = solve(problem, candidates, 2, small_grid.window)
    exact = brute_force(problem, candidates, 2)
    assert exact.value <= improved.value + 1e-9
    assert improved.value <= g.value + 1e-9
    assert len(np.unique(improved.sensors, axis=0)) == 2


def test_cvar_gradient_with_fractional_tail(small_grid):
    rng = np.random.default_rng(3)
    samples = rng.gamma(2, 1, (32, *small_grid.shape))
    field = IntensityField(small_grid, samples.mean(axis=0), samples=samples)
    problem = Problem(field, GaussianSensor(), "cvar", beta=0.9)
    sensors = np.array([[-0.7, 0.2], [1.1, 0.8]])
    _, gradient = problem.gradient(sensors)
    numerical = np.empty_like(gradient)
    for i, j in np.ndindex(sensors.shape):
        plus, minus = sensors.copy(), sensors.copy()
        plus[i, j] += 1e-6
        minus[i, j] -= 1e-6
        numerical[i, j] = (problem.value(plus) - problem.value(minus)) / 2e-6
    np.testing.assert_allclose(gradient, numerical, rtol=1e-5, atol=1e-6)


def test_drift_velocity_across_the_moebius_seam():
    scenario = make_scenario("seam_drift")
    history = [scenario.sample(t, np.random.default_rng(t), n=3000) for t in range(8)]
    fit = fm._fit_drift(history)
    assert fit.v[0] == pytest.approx(scenario.lanes[0].v_alpha, abs=0.002)
    assert fit.v[1] == pytest.approx(scenario.lanes[0].v_p, abs=0.03)


def test_bandwidth_scale_is_invariant_to_seam_representation():
    from stochplace.geometry import canonicalize
    from stochplace.intensity import scott_bandwidth

    rng = np.random.default_rng(8)
    a = rng.normal(0.0, 0.025, 200)
    p = rng.normal(0.5, 0.2, 200)
    seam = canonicalize(a, p)
    interior = canonicalize(a + np.pi / 2, p)
    np.testing.assert_allclose(scott_bandwidth(*seam), scott_bandwidth(*interior), rtol=1e-12)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -1.0])
def test_invalid_intensities_are_rejected(small_grid, bad):
    density = np.ones(small_grid.shape)
    density[0, 0] = bad
    with pytest.raises(ValueError):
        IntensityField(small_grid, density)


def test_mixture_rejects_different_grids(small_grid):
    other = RepGrid(Window(-2, 2, -1, 1), *small_grid.shape)
    with pytest.raises(ValueError):
        IntensityField.mixture(
            [
                IntensityField(small_grid, np.ones(small_grid.shape)),
                IntensityField(other, np.ones(other.shape)),
            ],
            [0.5, 0.5],
        )


def test_robustness_study_writes_honest_certificates(tmp_path):
    import pandas as pd

    from stochplace.robustness import RobustnessConfig, run_robustness

    cfg = RobustnessConfig(
        seeds=1,
        scenarios=("stationary",),
        radii=(0.0, 1.0),
        grid_shape=(24, 16),
        eval_grid_shape=(48, 32),
        candidate_spacing=5.0,
        n_sensors=2,
    )
    result = run_robustness(tmp_path, cfg, workers=1)
    assert len(result) == 8
    covered = result[result.certificate_applies_on_grid]
    assert len(covered) >= 4
    assert (covered.grid_detection_rate >= covered.worst_case_detection_rate - 1e-9).all()
    comparison = result.pivot(
        index=["scenario", "seed", "radius"], columns="strategy", values="worst_case_detection_rate"
    )
    assert (comparison.stacked_tv >= comparison.stacked - 1e-12).all()
    assert set(result[result.strategy == "stacked_tv"].tv_start) <= {"nominal_stacked", "tv_greedy"}
    summary = pd.read_csv(tmp_path / "summary.csv")
    assert len(summary) == 8


@pytest.mark.parametrize("label", ["stacked", "pseudo_bma", "mixture"])
@pytest.mark.parametrize("objective", ["void", "cvar"])
def test_uncalibrated_combiner_objectives_warn_without_refusing(small_grid, label, objective):
    density = np.ones(small_grid.shape)
    samples = None if label == "mixture" else np.stack([density, 2 * density])
    field = IntensityField(small_grid, density, samples=samples, label=label)
    message = "single mean field" if label == "mixture" else "not been validated for calibration"
    with pytest.warns(UserWarning, match=message):
        problem = Problem(field, GaussianSensor(), objective)
    assert np.isfinite(problem.value(np.array([[0.0, 0.0]])))


def test_failed_stacking_fit_uses_score_weights_and_records_reason(monkeypatch, small_grid):
    from types import SimpleNamespace

    history = make_scenario("drift").history(8, np.random.default_rng(8))
    config = ForecastConfig(n_samples=4, bandwidth=(0.04, 0.4))
    reference = forecast(history, small_grid, 2, "pseudo_bma", config)
    monkeypatch.setattr(
        fm, "minimize", lambda *args, **kw: SimpleNamespace(success=False, message="forced failure")
    )
    result = forecast(history, small_grid, 2, "stacked", config)
    assert result.label == "stacked"
    assert result.meta["weight_fit"] == "fallback_pseudo_bma"
    assert result.meta["weight_fit_message"] == "forced failure"
    assert result.meta["weights"] == reference.meta["weights"]
    np.testing.assert_allclose(result.density, reference.density, rtol=0, atol=0)
