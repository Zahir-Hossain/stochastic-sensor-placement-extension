"""Render the README animation from committed runs: one success case and one failure case.

The sensor plans and detection rates are read from ``results/``; nothing is
re-optimised here. Trajectories are regenerated with the same random streams
as the studies, so the pictured history is the history each plan was made from.
For each scenario the seed whose stacked-minus-history difference is closest
to the study mean is shown, so the frames are typical rather than selected.
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from PIL import Image

from stochplace import make_scenario
from stochplace.experiment import load_config
from stochplace.figures import COLORS, INK, INK2, MUTED, SURFACE
from stochplace.geometry import rep_to_lines

FUTURE = "#159a8c"
X = np.array([-11.0, 11.0])


def representative(runs: pd.DataFrame, keys: dict[str, object]) -> tuple[int, pd.DataFrame, float, int]:
    sub = runs
    for key, value in keys.items():
        sub = sub[np.isclose(sub[key], value)] if isinstance(value, float) else sub[sub[key] == value]
    wide = sub.pivot(index="seed", columns="strategy", values="detection_rate")
    gain = wide.stacked - wide.pooled
    seed = int((gain - gain.mean()).abs().idxmin())
    return seed, sub[sub.seed == seed].set_index("strategy"), float(100 * gain.mean()), len(gain)


def drift_case(results: Path) -> dict[str, object]:
    cfg = load_config("configs/suite_drift.yaml")
    runs = pd.read_csv(results / "suite_drift/runs.csv")
    seed, rows, mean_gain, n = representative(runs, {})
    scenario = make_scenario(cfg.scenario, **cfg.scenario_params)
    rng = np.random.default_rng([seed, 0, cfg.horizons[0]])
    history = scenario.history(cfg.history_epochs, rng)
    future = scenario.sample(cfg.history_epochs - 1 + cfg.horizons[0], rng)
    return {
        "title": "Designed drift: the forecast is right",
        "scenario": scenario,
        "history": history,
        "future": future,
        "rows": rows,
        "note": f"seed {seed}; mean over {n} seeds: {mean_gain:+.1f} pp for the forecast",
    }


def reversal_case(results: Path) -> dict[str, object]:
    runs = pd.read_csv(results / "robustness/runs.csv")
    seed, rows, mean_gain, n = representative(runs, {"scenario": "reversal", "radius": 0.0})
    scenario = make_scenario("reversal")
    history = scenario.history(8, np.random.default_rng(seed))
    future = scenario.sample(9, np.random.default_rng([seed, 9]))
    return {
        "title": "Drift reverses after training: the forecast is wrong",
        "scenario": scenario,
        "history": history,
        "future": future,
        "rows": rows,
        "note": f"seed {seed}; mean over {n} seeds: {mean_gain:+.1f} pp for the forecast",
    }


def draw_lines(
    ax: plt.Axes, alpha: np.ndarray, p: np.ndarray, colour: str, width: float, opacity: float
) -> None:
    if len(alpha) == 0:
        return
    m, b = rep_to_lines(alpha, p)
    ax.plot(
        np.tile(X, (len(m), 1)).T,
        (m[:, None] * X[None, :] + b[:, None]).T,
        color=colour,
        lw=width,
        alpha=opacity,
    )


def panel(ax: plt.Axes, case: dict[str, object], stage: int) -> None:
    """stage 0-7: history epochs; 8: plans; 9: future traffic; 10: result."""
    window = case["scenario"].window
    history = case["history"]
    ax.set_facecolor(SURFACE)
    ax.set_xlim(-10.8, 10.8)
    ax.set_ylim(-6.2, 6.2)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    shown = min(stage, 7)
    for epoch in range(shown + 1):
        a, p = history[epoch]
        current = epoch == shown and stage <= 7
        if stage >= 9:
            draw_lines(ax, a, p, MUTED, 0.5, 0.06)
        elif current:
            draw_lines(ax, a, p, INK, 0.7, 0.55)
        else:
            draw_lines(ax, a, p, MUTED, 0.5, 0.12 + 0.03 * epoch)
    if stage >= 9:
        draw_lines(ax, *case["future"], FUTURE, 0.8, 0.55)
    ax.add_patch(
        Rectangle(
            (window.xmin, window.ymin),
            window.xmax - window.xmin,
            window.ymax - window.ymin,
            fill=False,
            ec=INK2,
            lw=1.2,
            ls="--",
        )
    )
    rows = case["rows"]
    if stage >= 8:
        for strategy, marker in (("pooled", "s"), ("stacked", "o")):
            sensors = np.asarray(json.loads(rows.loc[strategy, "sensors"]))
            ax.plot(
                sensors[:, 0],
                sensors[:, 1],
                marker,
                ms=12,
                mfc="white",
                mec=COLORS[strategy],
                mew=2.6,
                ls="none",
                zorder=5,
            )
    if stage <= 7:
        status = f"Observed traffic, epoch {shown + 1} of 8"
    elif stage == 8:
        status = "Each method places 4 sensors"
    else:
        status = "Two epochs later: the real traffic"
    ax.set_title(case["title"], loc="left", fontsize=13, fontweight="bold", color=INK, pad=22)
    ax.text(0.0, 1.015, status, transform=ax.transAxes, fontsize=10.5, color=INK2, va="bottom")
    if stage >= 10:
        history_rate = 100 * rows.loc["pooled", "detection_rate"]
        forecast_rate = 100 * rows.loc["stacked", "detection_rate"]
        winner = "stacked" if forecast_rate > history_rate else "pooled"
        for i, (strategy, name, rate) in enumerate(
            (("pooled", "History", history_rate), ("stacked", "Forecast", forecast_rate))
        ):
            ax.text(
                0.02 + 0.5 * i,
                0.03,
                f"{name}  {rate:.1f}%",
                transform=ax.transAxes,
                fontsize=14,
                fontweight="bold" if strategy == winner else "normal",
                color=COLORS[strategy],
                bbox={"boxstyle": "round,pad=0.35", "fc": "white", "ec": COLORS[strategy], "lw": 1.5},
                zorder=6,
            )
        ax.text(
            0.99, -0.04, case["note"], transform=ax.transAxes, fontsize=8.5, color=MUTED, ha="right", va="top"
        )


def frame(cases: list[dict[str, object]], stage: int, card: bool = False) -> Image.Image:
    """Render one frame; ``card`` adds a headline for a 1280 x 640 social preview."""
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 6.4 if card else 5.0), dpi=100)
    fig.patch.set_facecolor("white")
    for ax, case in zip(axes, cases):
        panel(ax, case, stage)
    if card:
        fig.text(
            0.012,
            0.95,
            "When does forecast-aware sensor placement help?",
            fontsize=24,
            fontweight="bold",
            color=INK,
            va="top",
        )
        fig.text(0.012, 0.875, "stochplace", fontsize=13, color=INK2, va="top", family="monospace")
    fig.text(
        0.012,
        0.025,
        "Squares: sensors planned on history.   Circles: sensors planned on forecast stacking.   "
        "Score: expected share of future trajectories detected.",
        fontsize=9,
        color=INK2,
    )
    fig.subplots_adjust(
        left=0.01, right=0.99, top=0.72 if card else 0.84, bottom=0.1 if card else 0.12, wspace=0.05
    )
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--out", type=Path, default=Path("docs/figures/placement_story.gif"))
    args = parser.parse_args()
    cases = [drift_case(args.results), reversal_case(args.results)]
    stages = list(range(11))
    durations = [450] * 8 + [1400, 1600, 5000]
    images = [frame(cases, stage) for stage in stages]
    # Build one palette from representative frames plus solid swatches of the key
    # colours, so markers and score boxes keep their exact hues in every frame.
    width, height = images[0].size
    swatches = [COLORS["pooled"], COLORS["stacked"], FUTURE, INK, INK2, MUTED, SURFACE, "#ffffff"]
    sample = Image.new("RGB", (width, height * 3 + 40 * len(swatches)))
    for row, index in enumerate((4, 8, 10)):
        sample.paste(images[index], (0, row * height))
    for row, colour in enumerate(swatches):
        sample.paste(Image.new("RGB", (width, 40), colour), (0, height * 3 + 40 * row))
    palette = sample.quantize(colors=192, method=Image.Quantize.MEDIANCUT)
    frames = [image.quantize(palette=palette, dither=Image.Dither.NONE) for image in images]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        args.out,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=1,
    )
    images[-1].save(args.out.with_suffix(".png"), optimize=True)
    card = args.out.with_name("social_preview.png")
    frame(cases, stages[-1], card=True).save(card, optimize=True)
    print(f"Wrote {args.out} ({args.out.stat().st_size / 1e6:.2f} MB), its final frame and {card}")


if __name__ == "__main__":
    main()
