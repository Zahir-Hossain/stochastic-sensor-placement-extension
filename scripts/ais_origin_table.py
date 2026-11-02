"""Show the observed AIS origins and paired differences, without resampling."""

from __future__ import annotations

import numpy as np
import pandas as pd

FOCUSED_METHODS = [
    ("pooled", "Historical KDE"),
    ("recent", "Recent epochs"),
    ("lgcp", "Historical LGCP"),
    ("stacked", "Intensity stacking"),
    ("pseudo_bma", "Pseudo-BMA"),
    ("hindsight", "Hindsight heuristic"),
]

ALL_METHODS = [
    *FOCUSED_METHODS,
    ("stacked:void", "Stacked, expected void"),
    ("stacked:cvar", "Stacked, CVaR"),
    ("mixture", "Fixed intensity mixture"),
    ("drift_u", "Drift + uncertainty"),
    ("trend", "Log-linear trend"),
    ("fence", "Evenly spaced fence"),
    ("random", "Random baseline"),
]


def origin_tables(runs: pd.DataFrame, methods: list[tuple[str, str]]) -> tuple[str, str]:
    """Cells are detection percent [paired difference from historical KDE, pp]."""
    if runs.duplicated(["origin", "strategy"]).any():
        raise ValueError("duplicate AIS origin-strategy rows")
    rates = runs.pivot(index="strategy", columns="origin", values="detection_rate").sort_index(axis=1)
    if rates.isna().any().any() or not np.isfinite(rates.to_numpy()).all():
        raise ValueError("incomplete or non-finite AIS origins")
    if not rates.ge(0).all().all() or not rates.le(1).all().all():
        raise ValueError("AIS detection outside [0, 1]")
    baseline = rates.loc["pooled"]
    test_sizes = runs.groupby("origin").n_test
    if not test_sizes.nunique().eq(1).all():
        raise ValueError("methods use different test samples")
    origins = rates.columns.tolist()
    header = ["Planner", *[f"Origin {origin}" for origin in origins]]
    markdown = ["| " + " | ".join(header) + " |", "|---|" + "---:|" * len(origins)]
    tex = [" & ".join(header) + r" \\\midrule"]
    for method, title in methods:
        if method not in rates.index:
            continue
        row = rates.loc[method]
        cells = [f"{100 * row[o]:.1f} [{100 * (row[o] - baseline[o]):+.1f}]" for o in origins]
        markdown.append("| " + " | ".join([title, *cells]) + " |")
        tex.append(" & ".join([title.replace("&", r"\&"), *cells]) + r" \\")
    counts = "; ".join(f"origin {o}: {int(test_sizes.first().loc[o])} pieces" for o in origins)
    markdown += [
        "",
        "Each cell is expected detection (%) [paired difference from historical KDE, percentage points].",
        f"Test samples: {counts}.",
        "Origins overlap in training history. These values are descriptive and do not establish population-level significance.",
        "Generated from `results/ais_gothenburg/runs.csv` by the table generators and `scripts/ais_origin_table.py`.",
    ]
    return "\n".join(markdown) + "\n", "\n".join(tex) + "\n\\bottomrule\n"
