"""Command line interface: ``stochplace <command> ...``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__


def _cmd_run(args: argparse.Namespace) -> int:
    from .experiment import load_config, run_experiment

    for path in args.configs:
        cfg = load_config(path)
        if args.seeds is not None:
            cfg.seeds = args.seeds
        out = Path(args.out) / cfg.name
        print(
            f"running {cfg.name}: {len(cfg.settings())} settings x {len(cfg.horizons)} horizons x {cfg.seeds} seeds"
        )
        run_experiment(cfg, out, workers=args.workers)
        print(f"wrote {out}")
    return 0


def _cmd_figures(args: argparse.Namespace) -> int:
    from .figures import make_all

    make_all(Path(args.results), Path(args.out))
    return 0


def _cmd_ais(args: argparse.Namespace) -> int:
    from .ais import run_case_study

    run_case_study(Path(args.data), Path(args.out), workers=args.workers)
    return 0


def _cmd_legacy(args: argparse.Namespace) -> int:
    import numpy as np

    from .legacy import legacy_pipeline, legacy_routes

    s, b = legacy_routes(np.random.default_rng(args.seed))
    res = legacy_pipeline(s, b)
    for k, v in res.normalized_miss.items():
        print(f"{k:12s} normalized miss = {v:.6f}")
    return 0


def _cmd_robustness(args: argparse.Namespace) -> int:
    from .robustness import RobustnessConfig, plot_robustness, run_robustness

    out = Path(args.out)
    run_robustness(out, RobustnessConfig(seeds=args.seeds), workers=args.workers)
    plot_robustness(out, Path(args.figures))
    print(f"wrote {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="stochplace", description=__doc__)
    ap.add_argument("--version", action="version", version=f"stochplace {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run experiment config(s)")
    r.add_argument("configs", nargs="+")
    r.add_argument("--out", default="results")
    r.add_argument("--workers", type=int, default=None)
    r.add_argument(
        "--seeds", type=int, default=None, help="override number of seeds (e.g. for a quick check)"
    )
    r.set_defaults(func=_cmd_run)

    f = sub.add_parser("figures", help="build figures from results")
    f.add_argument("--results", default="results")
    f.add_argument("--out", default="docs/figures")
    f.set_defaults(func=_cmd_figures)

    a = sub.add_parser("ais", help="run the AIS case study")
    a.add_argument("--data", default="data/raw/ais.gpkg")
    a.add_argument("--out", default="results/ais_gothenburg")
    a.add_argument("--workers", type=int, default=None)
    a.set_defaults(func=_cmd_ais)

    lg = sub.add_parser("legacy", help="run the Python port of the v0.1 MATLAB toy")
    lg.add_argument("--seed", type=int, default=1)
    lg.set_defaults(func=_cmd_legacy)

    rb = sub.add_parser("robustness", help="TV robustness and forecast stress study")
    rb.add_argument("--seeds", type=int, default=20)
    rb.add_argument("--workers", type=int, default=2)
    rb.add_argument("--out", default="results/robustness")
    rb.add_argument("--figures", default="docs/figures")
    rb.set_defaults(func=_cmd_robustness)

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
