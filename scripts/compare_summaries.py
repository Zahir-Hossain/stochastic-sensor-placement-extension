"""Compare regenerated summaries against a recorded revision without changing tolerances."""

from __future__ import annotations

import argparse
import io
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd


def previous_csv(base: str, path: Path) -> pd.DataFrame:
    content = subprocess.check_output(["git", "show", f"{base}:{path.as_posix()}"])
    return pd.read_csv(io.BytesIO(content))


def ensure_baseline(base: str) -> None:
    available = subprocess.run(["git", "cat-file", "-e", f"{base}^{{commit}}"], capture_output=True)
    if available.returncode == 0:
        return
    bundle = Path("archive/research-history.bundle")
    if not bundle.exists() and Path("archive/history.json").exists():
        from restore_history import restore_bundle

        bundle = restore_bundle()
    if not bundle.exists():
        raise ValueError(f"baseline {base} is unavailable; fetch the full research history")
    subprocess.run(["git", "bundle", "verify", str(bundle)], check=True)
    subprocess.run(
        [
            "git",
            "fetch",
            str(bundle),
            "refs/heads/research-hardening:refs/remotes/review-history/research-hardening",
        ],
        check=True,
    )
    subprocess.run(["git", "cat-file", "-e", f"{base}^{{commit}}"], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base", default=json.loads(Path("docs/history/part_b_baseline.json").read_text())["pre_b_commit"]
    )
    parser.add_argument("--allow-robustness-change", action="store_true")
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--table", type=Path, default=Path("docs/tables/tv_before_after.md"))
    args = parser.parse_args()
    ensure_baseline(args.base)
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", args.base, "--", "results"], text=True
    )
    paths = [Path(p) for p in paths.splitlines() if p.endswith("/summary.csv")]
    for path in paths:
        old = previous_csv(args.base, path)
        new = pd.read_csv(args.results / path.relative_to("results"))
        keys = [
            c
            for c in old
            if c.startswith("param_")
            or c in ("scenario", "horizon", "radius", "scale", "strategy", "method", "policy")
        ]
        old = old.set_index(keys).sort_index()
        new = new.set_index(keys).sort_index()
        pd.testing.assert_index_equal(old.index, new.index)
        assert set(old.columns) == set(new.columns), f"{path}: schema differs"
        numeric = old.select_dtypes(include="number").columns
        changed = np.abs(new[numeric].to_numpy() - old[numeric].to_numpy())
        finite = changed[np.isfinite(changed)]
        maximum = float(finite.max()) if finite.size else 0.0
        if args.allow_robustness_change and path.parent.name == "robustness":
            unchanged = old.index.get_level_values("strategy") != "stacked_tv"
            np.testing.assert_allclose(
                new.loc[unchanged, numeric], old.loc[unchanged, numeric], rtol=0, atol=1e-9, equal_nan=True
            )
            print(f"EXPECTED CHANGE {path}: TV rows only; largest difference {maximum:.12g}")
        else:
            np.testing.assert_allclose(
                new[numeric], old[numeric], rtol=0, atol=1e-9, equal_nan=True, err_msg=str(path)
            )
            print(f"PASS {path}: {len(new)} rows, max absolute difference {maximum:.12g}")

    if args.allow_robustness_change:
        old = previous_csv(args.base, Path("results/robustness/summary.csv"))
        new = pd.read_csv(args.results / "robustness/summary.csv")
        keys = ["scenario", "radius", "strategy"]
        old = old.set_index(keys).sort_index()
        new = new.set_index(keys).sort_index()
        rows = [
            "| Scenario | Radius | Previous TV worst-case gain | New TV worst-case gain | Previous future gain | New future gain |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for key in old.index:
            if key[-1] != "stacked_tv":
                continue
            before, after = old.loc[key], new.loc[key]
            rows.append(
                f"| {key[0]} | {key[1]:g} | {before.worst_case_gain_vs_stacked_pp:+.4f} | "
                f"{after.worst_case_gain_vs_stacked_pp:+.4f} | {before.gain_vs_stacked_pp:+.4f} | "
                f"{after.gain_vs_stacked_pp:+.4f} |"
            )
        runs = pd.read_csv(args.results / "robustness/runs.csv")
        rates = runs.pivot(
            index=["scenario", "radius", "seed"], columns="strategy", values="worst_case_detection_rate"
        )
        assert (rates.stacked_tv >= rates.stacked - 1e-9).all(), (
            "TV search loses to its nominal feasible start"
        )
        rows += [
            "",
            "All gains are percentage points relative to the same nominal stacked plan.",
            "Generated by `scripts/compare_summaries.py` from the recorded pre-B summaries and current results.",
            f"Verified TV does not lose to nominal on its own objective in all {len(rates)} paired cases.",
        ]
        args.table.parent.mkdir(parents=True, exist_ok=True)
        args.table.write_text("\n".join(rows) + "\n")
    for path in args.results.glob("*/runs.csv"):
        runs = pd.read_csv(path)
        if "weight_fit" in runs:
            count = int(runs.weight_fit.eq("fallback_pseudo_bma").sum())
            print(f"Main-forecast fallback rows {path.parent.name}: {count}")
        else:
            print(f"Main-forecast fallback rows {path.parent.name}: not recorded")
        for column in ("calibration_backtests", "residual_backtests"):
            if column not in runs:
                continue
            prefix_fits = {}
            for _, row in runs.iterrows():
                for fit in json.loads(row[column]) if isinstance(row[column], str) else []:
                    prefix_fits[(row.get("scenario"), row.get("seed"), fit["target"])] = fit
            failures = sum(fit["weight_fit"] == "fallback_pseudo_bma" for fit in prefix_fits.values())
            print(
                f"Recorded calibration-prefix fits {path.parent.name}: {len(prefix_fits)}; fallbacks {failures}"
            )
    print(f"All {len(paths)} saved CSV summaries passed the comparison policy (absolute tolerance 1e-9).")


if __name__ == "__main__":
    main()
