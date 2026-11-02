"""How close is greedy to the exact optimum, and what does refinement add?

Random lane mixtures, k = 3 sensors, 45 grid candidates (14,190 subsets),
so the exact best subset can be found by enumeration.

Usage: python scripts/approximation_study.py [--instances 100] [--out results/approximation]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from stochplace import GaussianSensor, Lane, Problem, RepGrid, Scenario, brute_force, greedy, refine
from stochplace.experiment import _dependency_versions, _git_commit, _source_hash
from stochplace.scenarios import DEFAULT_WINDOW


def random_scenario(rng: np.random.Generator) -> Scenario:
    lanes = []
    for _ in range(rng.integers(1, 4)):
        lanes.append(
            Lane.from_slope(
                float(rng.uniform(-0.5, 0.5)),
                float(rng.uniform(-3.5, 3.5)),
                float(rng.uniform(0.03, 0.1)),
                float(rng.uniform(0.4, 1.5)),
                logit=float(rng.normal()),
            )
        )
    return Scenario("random", lanes, DEFAULT_WINDOW, rate=100.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", type=int, default=100)
    ap.add_argument("--out", default="results/approximation")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    grid = RepGrid(DEFAULT_WINDOW, 90, 48)
    model = GaussianSensor(0.95, 1.0)
    cand = DEFAULT_WINDOW.grid(2.5)
    k = 3
    rows = []
    for i in range(args.instances):
        rng = np.random.default_rng(1000 + i)
        sc = random_scenario(rng)
        prob = Problem(sc.truth(grid, 0.0), model)
        total = prob.field.total()
        g = greedy(prob, cand, k)
        b = brute_force(prob, cand, k)
        r = refine(prob, g, DEFAULT_WINDOW)
        rows.append(
            {
                "instance": i,
                "n_lanes": len(sc.lanes),
                "detected_greedy": total - g.value,
                "detected_opt": total - b.value,
                "detected_refined": total - r.value,
                "total": total,
                "ratio": (total - g.value) / (total - b.value),
                "greedy_is_opt": bool(np.isclose(g.value, b.value)),
                "refine_gain_pp": 100 * (b.value - r.value) / total,
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(out / "runs.csv", index=False)
    summary = {
        "instances": len(df),
        "min_ratio": float(df.ratio.min()),
        "mean_ratio": float(df.ratio.mean()),
        "frac_greedy_optimal": float(df.greedy_is_opt.mean()),
        "bound": 1 - 1 / np.e,
        "mean_refine_gain_over_grid_opt_pp": float(df.refine_gain_pp.mean()),
        "frac_refined_beats_grid_opt": float((df.detected_refined > df.detected_opt + 1e-9).mean()),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    meta = {
        "instances": args.instances,
        "source_sha256": _source_hash(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "git_commit": _git_commit(),
        "dependencies": _dependency_versions(),
        "candidate_count": len(cand),
        "n_sensors": k,
        "grid_shape": grid.shape,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
