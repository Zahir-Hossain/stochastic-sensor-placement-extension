"""Quickstart: plan sensors for where traffic is going, not where it was.

Run:  python examples/quickstart.py
"""

import numpy as np

import stochplace as sp

# 1. A lane of straight-line trajectories that drifts over time.
scenario = sp.make_scenario("drift", speed=0.3)
rng = np.random.default_rng(0)
history = scenario.history(8, rng)  # 8 observed epochs of (alpha, p) lines
horizon = 2  # plan for 2 epochs after the last observation

# 2. One grid over representation space shared by every estimate.
grid = sp.RepGrid(scenario.window, n_alpha=120, n_p=64)
model = sp.GaussianSensor(rho=0.95, r=1.0)
candidates = scenario.window.grid(1.0)

# 3. Two planners: history only (the classic approach) and the stacked forecast.
historical = sp.forecast(history, grid, horizon, "pooled")
stacked = sp.forecast(history, grid, horizon, "stacked")
print("stacking weights:", {k: round(v, 3) for k, v in stacked.meta["weights"].items()})

placements = {
    name: sp.solve(sp.Problem(field, model), candidates, k=4, window=scenario.window)
    for name, field in [("historical", historical), ("stacked", stacked)]
}

# 4. Score both against the true future intensity (known for synthetic data).
truth = scenario.truth(grid, len(history) - 1 + horizon)
for name, pl in placements.items():
    s = sp.score_on_truth(pl.sensors, truth, model)
    print(
        f"{name:10s} detects {100 * s.detection_rate:5.2f}% of future trajectories   sensors: {np.round(pl.sensors, 2).tolist()}"
    )
