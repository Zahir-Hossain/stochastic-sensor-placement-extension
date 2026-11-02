"""Build and execute examples/tutorial.ipynb from the cells below.

Usage: python scripts/build_tutorial.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from nbconvert.preprocessors import ExecutePreprocessor

CELLS: list[tuple[str, str]] = [
    (
        "md",
        """# stochplace tutorial

This notebook walks through the whole pipeline on a drifting traffic lane:

1. trajectories as points in the `(alpha, p)` line space,
2. intensity estimation and forecasting,
3. sensor placement by void probability,
4. scoring placements on the **true future**, not on the data they were planned on.

It runs in about a minute.""",
    ),
    (
        "code",
        """import matplotlib.pyplot as plt
import numpy as np

import stochplace as sp

rng = np.random.default_rng(0)
scenario = sp.make_scenario("drift", speed=0.3)
history = scenario.history(8, rng)          # list of (alpha, p) arrays, one per epoch
print([len(a) for a, _ in history], "lines per epoch")""",
    ),
    (
        "md",
        """## 1. Lines are points

A line `x cos(alpha) + y sin(alpha) = p` is the point `(alpha, p)`. The lane drifts, so the cloud of points moves from epoch to epoch.""",
    ),
    (
        "code",
        """fig, ax = plt.subplots(figsize=(6, 4))
for t, (a, p) in enumerate(history):
    ax.scatter(a, p, s=6, color=plt.cm.Blues(0.3 + 0.7 * t / 7), label=f"epoch {t}" if t in (0, 7) else None)
ax.set(xlabel="alpha", ylabel="p", title="Observed lines, colored by epoch")
ax.legend();""",
    ),
    (
        "md",
        """## 2. Intensity: history vs forecast

All estimates share one grid. `pooled` uses all history. `stacked` learns simplex weights by the held-out Poisson score of the combined intensity. Every validation origin refits bandwidth on its training prefix. The separate `pseudo_bma` baseline uses individual model scores.""",
    ),
    (
        "code",
        """grid = sp.RepGrid(scenario.window, 120, 64)
horizon = 2
pooled = sp.forecast(history, grid, horizon, "pooled")
stacked = sp.forecast(history, grid, horizon, "stacked")
truth = scenario.truth(grid, len(history) - 1 + horizon)
print("stacking weights:", {k: round(v, 3) for k, v in stacked.meta["weights"].items()})
print(f"L1 error vs true future: pooled {pooled.l1(truth):.1f}, stacked {stacked.l1(truth):.1f}")""",
    ),
    (
        "code",
        """fig, axes = plt.subplots(1, 3, figsize=(12, 3.2), sharey=True)
for ax, (f, name) in zip(axes, [(pooled, "pooled history"), (stacked, "stacked forecast"), (truth, "true future")]):
    ax.imshow(f.density.T, origin="lower", aspect="auto", cmap="Blues", extent=(0, np.pi, -grid.p_max, grid.p_max))
    ax.set(xlim=(1.45, 2.3), ylim=(-6, 8), title=name, xlabel="alpha")
axes[0].set_ylabel("p");""",
    ),
    (
        "md",
        """## 3. Place sensors

Greedy selection on a candidate grid (within `1 - 1/e` of the best subset for the expected objective), then gradient refinement.""",
    ),
    (
        "code",
        """model = sp.GaussianSensor(rho=0.95, r=1.0)
cand = scenario.window.grid(1.0)
plans = {name: sp.solve(sp.Problem(f, model), cand, 4, scenario.window)
         for name, f in [("pooled", pooled), ("stacked", stacked), ("oracle", truth)]}
for name, pl in plans.items():
    print(f"{name:8s}", np.round(pl.sensors, 2).tolist())""",
    ),
    (
        "md",
        """## 4. Score on the future

The oracle is the same heuristic given true future intensity. It is a useful reference, not a certified continuous optimum. A detection fraction is distinct from the chance that no trajectory is missed in an epoch.""",
    ),
    (
        "code",
        """for name, pl in plans.items():
    s = sp.score_on_truth(pl.sensors, truth, model)
    print(f"{name:8s} detection {100 * s.detection_rate:6.2f}%   P(no ship missed in an epoch) = {s.void_probability:.3g}")""",
    ),
    (
        "md",
        """## 5. Uncertainty and robust objectives

The expected objective needs only the predictive mean. `void` maximises expected void probability and emphasises favourable futures; it is not a worst-case penalty. `cvar` targets the worst 10% of sampled miss counts, including fractional mass at the quantile. All three are evaluated on the same future truth.""",
    ),
    (
        "code",
        """drift_u = sp.forecast(history, grid, horizon, "drift_u")
for obj in ("expected", "void", "cvar"):
    pl = sp.solve(sp.Problem(drift_u, model, objective=obj), cand, 4, scenario.window)
    print(f"{obj:8s} detection on true future: {100 * sp.score_on_truth(pl.sensors, truth, model).detection_rate:.2f}%")""",
    ),
]

CELLS.extend(
    [
        (
            "md",
            """## 6. A conditional grid robustness certificate

The TV objective allows an adversary to redistribute a declared fraction of traffic mass. Its inner solution is exact on the planning grid. The outer sensor search remains a heuristic, and the certificate applies only when the normalised future grid truth is inside the ambiguity ball.""",
        ),
        (
            "code",
            """coarse = sp.RepGrid(scenario.window, 72, 48)
field = sp.forecast(history, coarse, horizon, "stacked")
robust = sp.Problem(field, model, "tv", radius=0.15)
plan = sp.solve(robust, scenario.window.grid(2.5), 4, scenario.window)
adversary = sp.tv_adversary(robust.w_mean, robust.miss(plan.sensors), robust.radius)
future = scenario.truth(coarse, 9)
distance = 0.5 * np.abs(future.mass / future.total() - field.mass / field.total()).sum()
print(f"Grid worst-case detection: {1 - adversary.value / field.total():.2%}")
print(f"Future expected detection on same grid: {sp.score_on_truth(plan.sensors, future, model).detection_rate:.2%}")
print(f"Future-to-forecast TV distance: {distance:.3f}; radius: {robust.radius:.3f}")
print("Certificate applies to this truth:", bool(distance <= robust.radius))""",
        ),
        (
            "md",
            """## 7. A forecast assumption can fail

In `reversal`, the lane reverses after the history ends. The model is not told about the turn. Compare planning on history with extrapolation. This is one illustrative seed; the checked-in stress study uses 20 paired seeds.""",
        ),
        (
            "code",
            """reversal = sp.make_scenario("reversal")
past = reversal.history(8, np.random.default_rng(0))
g = sp.RepGrid(reversal.window, 72, 48)
future = reversal.truth(g, 9)
for method in ("pooled", "drift_u", "stacked"):
    f = sp.forecast(past, g, 2, method)
    pl = sp.solve(sp.Problem(f, model), reversal.window.grid(2.5), 4, reversal.window)
    print(f"{method:8s}: {sp.score_on_truth(pl.sensors, future, model).detection_rate:.2%} future expected detection")""",
        ),
    ]
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="execute with IPython when local kernel sockets are unavailable",
    )
    args = parser.parse_args()
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_markdown_cell(src) if kind == "md" else nbformat.v4.new_code_cell(src)
        for kind, src in CELLS
    ]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    if args.in_process:
        import base64
        from io import BytesIO

        import matplotlib.pyplot as plt
        from IPython.core.interactiveshell import InteractiveShell
        from IPython.utils.capture import capture_output

        shell = InteractiveShell.instance()
        count = 0
        for cell in nb.cells:
            if cell.cell_type != "code":
                continue
            count += 1
            with capture_output() as captured:
                result = shell.run_cell(cell.source, store_history=False)
            if result.error_before_exec or result.error_in_exec:
                raise RuntimeError(f"notebook cell {count} failed") from (
                    result.error_before_exec or result.error_in_exec
                )
            outputs = []
            if captured.stdout:
                outputs.append(nbformat.v4.new_output("stream", name="stdout", text=captured.stdout))
            if captured.stderr:
                outputs.append(nbformat.v4.new_output("stream", name="stderr", text=captured.stderr))
            outputs.extend(
                nbformat.v4.new_output("display_data", data=item.data, metadata=item.metadata)
                for item in captured.outputs
            )
            for number in plt.get_fignums():
                figure = plt.figure(number)
                buffer = BytesIO()
                figure.savefig(buffer, format="png", dpi=130, bbox_inches="tight")
                outputs.append(
                    nbformat.v4.new_output(
                        "display_data",
                        data={"image/png": base64.b64encode(buffer.getvalue()).decode("ascii")},
                    )
                )
                plt.close(figure)
            cell.execution_count, cell.outputs = count, outputs
    else:
        km = KernelManager(kernel_name="python3")
        km.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
        ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(
            nb, {"metadata": {"path": "."}}, km=km
        )
    out = Path("examples/tutorial.ipynb")
    nbformat.write(nb, out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
