import numpy as np
import pytest

from stochplace import (
    DiskSensor,
    GaussianSensor,
    IntensityField,
    LogisticSensor,
    Problem,
    RepGrid,
    make_scenario,
    miss_probability_lines,
)
from stochplace.sensors import sensor_from_config


def test_grid_miss_matches_exact_lines(window, sensor, rng):
    """Cell-centre evaluation of q agrees with exact per-line evaluation."""
    g = RepGrid(window, 240, 128)
    sc = make_scenario("stationary")
    truth = sc.truth(g, 0)
    prob = Problem(truth, sensor)
    S = np.array([[-1.0, -1.0], [1.0, 0.5], [0.0, 2.0]])
    lam = prob.lambda_miss(S) / truth.total()
    a, p = sc.sample(0, rng, n=200_000)
    mc = miss_probability_lines(S, a, p, sensor).mean()
    assert abs(lam - mc) < 0.01


@pytest.mark.slow
def test_void_probability_matches_simulation(window):
    """Poisson thinning: P(no undetected line) = exp(-Lambda_miss)."""
    sensor = GaussianSensor(0.95, 1.0)
    sc = make_scenario("stationary").with_rate(25.0)
    g = RepGrid(window, 240, 128)
    truth = sc.truth(g, 0)
    S = np.array([[-1.0, -1.5], [0.5, 0.0], [1.0, 2.0], [-2.0, 1.0]])
    lam = float(Problem(truth, sensor).lambda_miss(S))
    rng = np.random.default_rng(7)
    n_epochs = 20_000
    undetected = np.empty(n_epochs)
    for e in range(n_epochs):
        a, p = sc.sample(0, rng)
        q = miss_probability_lines(S, a, p, sensor)
        undetected[e] = (rng.random(len(q)) < q).sum()
    void_mc = float(np.mean(undetected == 0))
    se = np.sqrt(void_mc * (1 - void_mc) / n_epochs)
    assert abs(undetected.mean() - lam) < 4 * undetected.std() / np.sqrt(n_epochs) + 0.02
    assert abs(void_mc - np.exp(-lam)) < 4 * se + 0.01


@pytest.mark.parametrize("model", [GaussianSensor(0.9, 1.2), LogisticSensor(0.9, 1.5, 0.3)])
@pytest.mark.parametrize("objective", ["expected", "void", "cvar"])
def test_gradient_matches_finite_differences(small_grid, model, objective):
    rng = np.random.default_rng(0)
    dens = rng.gamma(2.0, 1.0, small_grid.shape)
    samples = dens[None] * rng.gamma(4.0, 0.25, (20, *small_grid.shape))
    f = IntensityField(small_grid, dens, samples=samples)
    prob = Problem(f, model, objective=objective, beta=0.8)
    S = rng.uniform(-1.5, 1.5, (3, 2))
    v, gr = prob.gradient(S)
    assert np.isclose(v, prob.value(S))
    eps = 1e-6
    num = np.zeros_like(S)
    for i in range(3):
        for j in range(2):
            Sp, Sm = S.copy(), S.copy()
            Sp[i, j] += eps
            Sm[i, j] -= eps
            num[i, j] = (prob.value(Sp) - prob.value(Sm)) / (2 * eps)
    tol = 1e-4 if objective != "cvar" else 1e-3
    np.testing.assert_allclose(gr, num, rtol=tol, atol=tol * max(1.0, np.abs(num).max()))


def test_expected_objective_is_linear(small_grid, sensor):
    """E_samples[Lambda_miss] equals Lambda_miss at the mean intensity."""
    rng = np.random.default_rng(1)
    samples = rng.gamma(2.0, 1.0, (16, *small_grid.shape))
    f = IntensityField(small_grid, samples.mean(axis=0), samples=samples)
    prob = Problem(f, sensor)
    S = rng.uniform(-2, 2, (3, 2))
    per = prob.lambda_miss(S, per_sample=True)
    assert np.isclose(np.mean(per), prob.lambda_miss(S))


def test_robust_objectives_order(small_grid, sensor):
    """cvar >= expected and void <= expected (Jensen) for the same sensors."""
    rng = np.random.default_rng(2)
    samples = rng.gamma(1.0, 1.0, (32, *small_grid.shape))
    f = IntensityField(small_grid, samples.mean(axis=0), samples=samples)
    S = rng.uniform(-2, 2, (2, 2))
    e = Problem(f, sensor, "expected").value(S)
    c = Problem(f, sensor, "cvar", beta=0.75).value(S)
    v = Problem(f, sensor, "void").value(S)
    assert c >= e - 1e-9
    assert v <= e + 1e-9


def test_monotone_submodular(small_grid, sensor):
    """Detected mass F(S) = total - Lambda_miss(S) is monotone and submodular."""
    rng = np.random.default_rng(3)
    f = IntensityField(small_grid, rng.gamma(2.0, 1.0, small_grid.shape))
    prob = Problem(f, sensor)
    total = f.total()

    def F(S):
        return total - prob.lambda_miss(np.array(S)) if len(S) else 0.0

    for _ in range(200):
        pts = [tuple(x) for x in rng.uniform(-3, 3, (5, 2))]
        A = pts[:2]
        B = pts[:4]
        e = pts[4]
        assert F(B) >= F(A) - 1e-9
        assert F([*A, e]) - F(A) >= F([*B, e]) - F(B) - 1e-9


def test_disk_and_config():
    d = DiskSensor(0.8, 1.0)
    assert d.prob(np.array([0.5]))[0] == 0.8
    assert d.prob(np.array([1.5]))[0] == 0.0
    assert not d.smooth
    assert isinstance(sensor_from_config({"type": "gaussian", "r": 2}), GaussianSensor)
    assert isinstance(sensor_from_config({"type": "logistic"}), LogisticSensor)
    assert isinstance(sensor_from_config({"type": "disk", "R": 1}), DiskSensor)
    with pytest.raises(ValueError):
        sensor_from_config({"type": "laser"})
    with pytest.raises(ValueError):
        GaussianSensor(1.5, 1.0)


def test_problem_validation(small_grid, sensor):
    f = IntensityField(small_grid, np.ones(small_grid.shape))
    with pytest.raises(ValueError):
        Problem(f, sensor, objective="median")
    with pytest.raises(ValueError):
        Problem(f, sensor, beta=1.0)
    with pytest.raises(ValueError):
        Problem(f, DiskSensor()).gradient(np.zeros((1, 2)))
    assert np.all(Problem(f, sensor).miss(np.empty((0, 2))) == 1)
