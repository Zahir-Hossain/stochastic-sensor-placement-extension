"""Inspect a finite-grid robustness certificate, including its scope."""

import numpy as np

import stochplace as sp

scenario = sp.make_scenario("reversal")
history = scenario.history(8, np.random.default_rng(0))
grid = sp.RepGrid(scenario.window, 72, 48)
field = sp.forecast(history, grid, 2, "stacked")
problem = sp.Problem(field, sp.GaussianSensor(), "tv", radius=0.15)
plan = sp.solve(problem, scenario.window.grid(2.5), 4, scenario.window)
worst = sp.tv_adversary(problem.w_mean, problem.miss(plan.sensors), problem.radius)
truth = scenario.truth(grid, 9)
distance = 0.5 * np.abs(truth.mass / truth.total() - field.mass / field.total()).sum()
print("Sensors:", plan.sensors.tolist())
print(f"Worst-case expected detection on planning grid: {1 - worst.value / field.total():.2%}")
print(
    f"True-future expected detection on that grid: {sp.score_on_truth(plan.sensors, truth, problem.model).detection_rate:.2%}"
)
print(f"Distance of future shape from forecast: {distance:.3f}; chosen radius: {problem.radius:.3f}")
print("Certificate applies to this truth:", bool(distance <= problem.radius))
print("The outer sensor search is a heuristic; the inner adversarial mass is exact on this grid.")
