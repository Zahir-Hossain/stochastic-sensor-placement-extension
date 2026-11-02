"""Real-traffic case study on AIS vessel tracks.

The bundled study uses one day (5 July 2017) of AIS data near the port of
Gothenburg, published by the Danish Maritime Authority and redistributed
as ``ais.gpkg`` in the MovingPandas examples repository. Run
``python scripts/fetch_ais_sample.py`` to download it.

Pipeline
--------
1. read point reports from the GeoPackage (sqlite + WKB, no GIS stack);
2. project lon/lat to a local tangent plane in km;
3. cut each vessel's track into passages through the barrier window
   (time gaps split passages; stationary reports are dropped);
4. approximate each passage by straight pieces (total least squares,
   split recursively where a single line fits badly), as in the local
   linear approximation of Kim et al.;
5. map each piece to ``(alpha, p)`` and group pieces into time epochs.

Evaluation is rolling-origin: plan from epochs ``< T`` and score the
placement on the lines actually observed in epoch ``T``.
"""

from __future__ import annotations

import json
import sqlite3
import struct
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from ._typing import FloatArray
from .evaluate import bootstrap_ci, score_on_lines
from .forecast import ForecastConfig, _bandwidth, forecast
from .geometry import Window, fit_line_tls
from .grid import IntensityField, RepGrid
from .intensity import kde_intensity, lgcp_intensity
from .objective import Problem
from .optimize import fence_placement, random_placement, solve
from .sensors import GaussianSensor

__all__ = [
    "AISStudyConfig",
    "extract_lines",
    "project",
    "read_gpkg_points",
    "run_case_study",
]

#: Barrier window (km, local tangent plane) covering the main fairway and
#: the crossing lane at the mouth of the Goeta aelv.
GOTHENBURG_WINDOW = Window(-2.5, 2.5, -1.0, 1.5)
GOTHENBURG_ORIGIN = (11.856451, 57.679491)  # lon, lat of the data centroid


def _wkb_point(blob: bytes) -> tuple[float, float]:
    """Decode a GeoPackage point geometry (header + little/big endian WKB)."""
    if blob[:2] != b"GP":
        raise ValueError("not a GeoPackage geometry blob")
    flags = blob[3]
    env = (flags >> 1) & 0b111
    env_len = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[env]
    off = 8 + env_len
    order = "<" if blob[off] == 1 else ">"
    (gtype,) = struct.unpack(order + "I", blob[off + 1 : off + 5])
    if gtype % 1000 != 1:
        raise ValueError(f"expected a point geometry, got WKB type {gtype}")
    x, y = struct.unpack(order + "dd", blob[off + 5 : off + 21])
    return x, y


def read_gpkg_points(path: str | Path) -> pd.DataFrame:
    """Read AIS point reports from the DMA/MovingPandas GeoPackage."""
    con = sqlite3.connect(str(path))
    try:
        (table,) = con.execute("select table_name from gpkg_contents where data_type='features'").fetchone()
        rows = con.execute(
            f'select geom, Timestamp, MMSI, SOG, COG, ShipType, NavStatus from "{table}"'
        ).fetchall()
    finally:
        con.close()
    xy = np.array([_wkb_point(r[0]) for r in rows])
    ts = pd.to_datetime([r[1] for r in rows], format="%d/%m/%Y %H:%M:%S")
    return pd.DataFrame(
        {
            "lon": xy[:, 0],
            "lat": xy[:, 1],
            "time": ts,
            "mmsi": [r[2] for r in rows],
            "sog": [r[3] if r[3] is not None else np.nan for r in rows],
            "cog": [r[4] if r[4] is not None else np.nan for r in rows],
            "ship_type": [r[5] for r in rows],
            "nav_status": [r[6] for r in rows],
        }
    )


def project(lon: FloatArray, lat: FloatArray, origin: tuple[float, float]) -> tuple[FloatArray, FloatArray]:
    """Local equirectangular projection to km (error < 0.1 % over ~10 km)."""
    lon0, lat0 = origin
    x = (np.asarray(lon) - lon0) * 111.320 * np.cos(np.radians(lat0))
    y = (np.asarray(lat) - lat0) * 110.574
    return x, y


def _split_linear(
    xy: FloatArray,
    idx: NDArray[np.int64],
    min_points: int,
    min_linearity: float,
    max_dev: float = np.inf,
    depth: int = 0,
) -> list[NDArray[np.int64]]:
    """Recursively split a track until each piece is close to a straight line.

    A piece is accepted when its points are nearly collinear (eigenvalue
    ratio ``>= min_linearity``) and no report is farther than ``max_dev``
    from the fitted line. Otherwise it is split at the report farthest
    from the chord between its end points (Douglas-Peucker). Returns
    index arrays into ``xy``.
    """
    if len(idx) < min_points:
        return []
    pts = xy[idx]
    a, p, lin = fit_line_tls(pts)
    dev = float(np.max(np.abs(pts[:, 0] * np.cos(a) + pts[:, 1] * np.sin(a) - p)))
    if lin >= min_linearity and dev <= max_dev:
        return [idx]
    if len(idx) < 2 * min_points or depth >= 6:
        return []
    chord = pts[-1] - pts[0]
    norm = float(np.hypot(*chord))
    if norm > 0:
        d = np.abs(chord[0] * (pts[:, 1] - pts[0, 1]) - chord[1] * (pts[:, 0] - pts[0, 0])) / norm
    else:
        d = np.hypot(pts[:, 0] - pts[0, 0], pts[:, 1] - pts[0, 1])
    k = int(np.clip(np.argmax(d), min_points, len(idx) - min_points))
    return _split_linear(xy, idx[:k], min_points, min_linearity, max_dev, depth + 1) + _split_linear(
        xy, idx[k:], min_points, min_linearity, max_dev, depth + 1
    )


def _epoch_ids(times: pd.Series, hours: float, origin: pd.Timestamp) -> NDArray[np.int64]:
    """Calendar-origin epoch IDs, shared by extraction and study grouping."""
    if not np.isfinite(hours) or hours <= 0:
        raise ValueError("epoch_hours must be positive")
    width = round(hours * 3600 * 1e9)
    if width < 1 or pd.isna(origin):
        raise ValueError("epoch width and origin must be valid")
    stamps = pd.to_datetime(times).dt.as_unit("ns").astype("int64").to_numpy()
    return np.asarray((stamps - origin.value) // width, dtype=np.int64)


def extract_lines(
    df: pd.DataFrame,
    window: Window,
    origin: tuple[float, float] = GOTHENBURG_ORIGIN,
    *,
    min_sog: float = 1.0,
    max_gap_s: float = 600.0,
    min_points: int = 5,
    min_length_km: float = 0.3,
    min_linearity: float = 0.98,
    max_dev_km: float = 0.05,
    epoch_hours: float | None = None,
    epoch_origin: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Turn AIS reports into straight trajectory pieces in ``(alpha, p)``.

    A piece is kept if it has at least ``min_points`` reports, is at least
    ``min_length_km`` long and no report lies more than ``max_dev_km`` from
    its fitted line. Returns one row per piece with its representation,
    mid time, vessel id, ship type, number of reports and length.
    """
    epoch_origin = epoch_origin if epoch_origin is not None else pd.Timestamp(df["time"].min()).normalize()
    x, y = project(df["lon"].to_numpy(), df["lat"].to_numpy(), origin)
    eligible = (df["sog"].to_numpy() >= min_sog) & window.contains(np.column_stack([x, y]))
    d = df.assign(x=x, y=y, eligible=eligible)
    out: list[dict[str, Any]] = []
    for _mmsi, g in d.sort_values("time").groupby("mmsi"):
        t = g["time"].to_numpy()
        gaps = np.diff(t).astype("timedelta64[s]").astype(float)
        good = g["eligible"].to_numpy(bool)
        split = (gaps > max_gap_s) | ~good[:-1] | ~good[1:]
        if epoch_hours is not None:
            epoch_id = _epoch_ids(g["time"], epoch_hours, epoch_origin)
            split |= np.diff(epoch_id) != 0
        cut = np.flatnonzero(split) + 1
        for seg_idx in np.split(np.arange(len(g)), cut):
            seg = cast(pd.DataFrame, g.iloc[seg_idx])
            if not seg["eligible"].all():
                continue
            xy = seg[["x", "y"]].to_numpy()
            times = seg["time"].to_numpy()
            for piece in _split_linear(xy, np.arange(len(xy)), min_points, min_linearity, max_dev_km):
                piece_xy = xy[piece]
                length = float(np.linalg.norm(piece_xy[-1] - piece_xy[0]))
                if length < min_length_km:
                    continue
                a, p, lin = fit_line_tls(piece_xy)
                tt = times[piece]
                out.append(
                    {
                        "alpha": a,
                        "p": p,
                        "linearity": lin,
                        "t_mid": pd.Timestamp(tt.min() + (tt.max() - tt.min()) / 2),
                        "start_time": pd.Timestamp(tt.min()),
                        "end_time": pd.Timestamp(tt.max()),
                        "mmsi": int(seg["mmsi"].iloc[0]),
                        "ship_type": seg["ship_type"].iloc[0],
                        "n_reports": len(piece_xy),
                        "length_km": length,
                        "x0": piece_xy[0, 0],
                        "y0": piece_xy[0, 1],
                        "x1": piece_xy[-1, 0],
                        "y1": piece_xy[-1, 1],
                    }
                )
    return pd.DataFrame(
        out,
        columns=[
            "alpha",
            "p",
            "linearity",
            "t_mid",
            "start_time",
            "end_time",
            "mmsi",
            "ship_type",
            "n_reports",
            "length_km",
            "x0",
            "y0",
            "x1",
            "y1",
        ],
    )


@dataclass
class AISStudyConfig:
    window: Window = GOTHENBURG_WINDOW
    epoch_hours: float = 3.0
    first_origin: int = 4
    n_sensors: int = 4
    sensor_rho: float = 0.95
    sensor_r_km: float = 0.15
    candidate_spacing_km: float = 0.1
    grid_shape: tuple[int, int] = (120, 64)
    lgcp_fit_shape: tuple[int, int] = (60, 32)
    strategies: tuple[str, ...] = (
        "pooled",
        "lgcp",
        "recent",
        "drift_u",
        "trend",
        "mixture",
        "stacked",
        "pseudo_bma",
        "stacked:void",
        "stacked:cvar",
        "hindsight",
        "fence",
        "random",
    )
    n_random: int = 50


def _epochs(
    lines: pd.DataFrame, hours: float, origin: pd.Timestamp | None = None
) -> list[tuple[FloatArray, FloatArray]]:
    day0 = origin if origin is not None else pd.Timestamp(lines["start_time"].min()).normalize()
    e = _epoch_ids(lines["t_mid"], hours, day0)
    n = int(e.max()) + 1
    return [(lines.loc[e == k, "alpha"].to_numpy(), lines.loc[e == k, "p"].to_numpy()) for k in range(n)]


def run_case_study(
    data: Path, out: Path, cfg: AISStudyConfig | None = None, workers: int | None = None
) -> pd.DataFrame:
    """Rolling-origin evaluation on the Gothenburg AIS sample."""
    cfg = cfg or AISStudyConfig()
    out.mkdir(parents=True, exist_ok=True)
    pts = read_gpkg_points(data)
    epoch_origin = pd.Timestamp(pts["time"].min()).normalize()
    lines = extract_lines(pts, cfg.window, epoch_hours=cfg.epoch_hours, epoch_origin=epoch_origin)
    if len(lines) == 0:
        raise ValueError("no valid straight passages remain after filtering")
    # publish derived lines with an anonymous vessel index instead of MMSI
    public = lines.assign(vessel=pd.factorize(lines["mmsi"])[0]).drop(columns=["mmsi"])
    public.to_csv(out / "lines.csv", index=False)
    epochs = _epochs(lines, cfg.epoch_hours, epoch_origin)
    grid = RepGrid(cfg.window, *cfg.grid_shape)
    model = GaussianSensor(cfg.sensor_rho, cfg.sensor_r_km)
    cand = cfg.window.grid(cfg.candidate_spacing_km)
    fcfg = ForecastConfig()
    rows: list[dict[str, Any]] = []
    for T in range(cfg.first_origin, len(epochs)):
        hist = epochs[:T]
        ta, tp = epochs[T]
        if len(ta) == 0:
            continue
        bw = _bandwidth(hist, fcfg)
        for strat in cfg.strategies:
            src, _, obj = strat.partition(":")
            obj = obj or "expected"
            if src == "fence":
                pr = Problem(IntensityField(grid, np.ones(grid.shape)), model)
                sensors = fence_placement(pr, cfg.window, cfg.n_sensors).sensors
            elif src == "random":
                pr = Problem(IntensityField(grid, np.ones(grid.shape)), model)
                rates = [
                    score_on_lines(
                        random_placement(
                            pr, cfg.window, cfg.n_sensors, np.random.default_rng([T, i])
                        ).sensors,
                        ta,
                        tp,
                        model,
                    ).detection_rate
                    for i in range(cfg.n_random)
                ]
                rows.append(
                    {
                        "origin": T,
                        "strategy": strat,
                        "detection_rate": float(np.mean(rates)),
                        "n_test": len(ta),
                    }
                )
                continue
            else:
                if src == "hindsight":
                    f = kde_intensity(ta, tp, grid, bandwidth=bw, label="hindsight")
                elif src == "lgcp":
                    a = np.concatenate([h[0] for h in hist])
                    p = np.concatenate([h[1] for h in hist])
                    f = lgcp_intensity(a, p, grid, n_epochs=T, fit_shape=cfg.lgcp_fit_shape).field
                else:
                    f = forecast(hist, grid, 1, src, fcfg, bw)
                sensors = solve(Problem(f, model, objective=obj), cand, cfg.n_sensors, cfg.window).sensors
            s = score_on_lines(sensors, ta, tp, model)
            rows.append(
                {
                    "origin": T,
                    "strategy": strat,
                    "detection_rate": s.detection_rate,
                    "n_test": len(ta),
                    "sensors": json.dumps(np.round(sensors, 4).tolist()),
                }
            )
    res = pd.DataFrame(rows)
    res.to_csv(out / "runs.csv", index=False)
    summ: list[dict[str, Any]] = []
    for strat_key, g in res.groupby("strategy", sort=False):
        # weight origins by number of test lines (pooled detection rate)
        w = g["n_test"].to_numpy(float)
        pooled = float(np.sum(g["detection_rate"] * w) / w.sum())
        m, lo, hi = bootstrap_ci(g["detection_rate"].to_numpy())
        summ.append(
            {
                "strategy": str(strat_key),
                "pooled_detection_rate": pooled,
                "mean_over_origins": m,
                "lo": lo,
                "hi": hi,
                "n_origins": len(g),
            }
        )
    pd.DataFrame(summ).to_csv(out / "summary.csv", index=False)
    meta = {
        "data": "Danish Maritime Authority AIS, 2017-07-05, Gothenburg (via movingpandas-examples/data/ais.gpkg)",
        "n_reports": len(pts),
        "epoch_origin": epoch_origin.isoformat(),
        "n_lines": len(lines),
        "lines_per_epoch": [len(e[0]) for e in epochs],
        "window_km": [cfg.window.xmin, cfg.window.xmax, cfg.window.ymin, cfg.window.ymax],
        "config": {k: (str(v) if isinstance(v, Window) else v) for k, v in cfg.__dict__.items()},
        "generated": datetime.now().isoformat(timespec="seconds"),
        "preprocessing": "split at epoch boundaries, time gaps, exits and low-speed reports before line fitting",
        "estimand": "expected detection probability per straight passage piece",
    }
    import hashlib

    from .experiment import _dependency_versions, _git_commit, _source_hash

    meta.update(
        {
            "data_sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
            "source_sha256": _source_hash(),
            "git_commit": _git_commit(),
            "dependencies": _dependency_versions(),
        }
    )
    (out / "meta.json").write_text(json.dumps(meta, indent=2, default=str))
    return res
