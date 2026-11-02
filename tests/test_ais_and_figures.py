import sqlite3
import struct
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from stochplace.ais import (
    AISStudyConfig,
    _wkb_point,
    extract_lines,
    project,
    read_gpkg_points,
    run_case_study,
)
from stochplace.geometry import Window, canonicalize

ORIGIN = (11.85, 57.68)


def _blob(lon: float, lat: float, big_endian: bool = False) -> bytes:
    order = ">" if big_endian else "<"
    header = b"GP" + bytes([0, 0b00000001]) + struct.pack("<i", 4326)  # no envelope
    wkb = (
        (b"\x00" if big_endian else b"\x01")
        + struct.pack(order + "I", 1)
        + struct.pack(order + "dd", lon, lat)
    )
    return header + wkb


def _write_gpkg(path, tracks):
    """tracks: list of (mmsi, list of (time, lon, lat, sog))."""
    con = sqlite3.connect(path)
    con.execute("create table gpkg_contents (table_name text, data_type text, srs_id int)")
    con.execute("insert into gpkg_contents values ('pts', 'features', 4326)")
    con.execute(
        "create table pts (fid integer primary key, geom blob, Timestamp text, MMSI int, "
        "SOG real, COG real, ShipType text, NavStatus text)"
    )
    for mmsi, rows in tracks:
        for t, lon, lat, sog in rows:
            con.execute(
                "insert into pts (geom, Timestamp, MMSI, SOG, COG, ShipType, NavStatus) values (?,?,?,?,?,?,?)",
                (_blob(lon, lat), t.strftime("%d/%m/%Y %H:%M:%S"), mmsi, sog, 0.0, "Cargo", "Under way"),
            )
    con.commit()
    con.close()


def _km_to_lonlat(x, y):
    lon = ORIGIN[0] + np.asarray(x) / (111.320 * np.cos(np.radians(ORIGIN[1])))
    lat = ORIGIN[1] + np.asarray(y) / 110.574
    return lon, lat


def _straight_tracks(n_vessels=12, hours=24, seed=0):
    rng = np.random.default_rng(seed)
    day = datetime(2017, 7, 5)
    tracks = []
    for v in range(n_vessels):
        start = day + timedelta(hours=float(rng.uniform(0, hours - 1)))
        slope = rng.normal(0.25, 0.05)
        b = rng.normal(0.2, 0.3)
        xs = np.linspace(-2.4, 2.4, 40)
        ys = slope * xs + b
        lon, lat = _km_to_lonlat(xs, ys)
        rows = [(start + timedelta(seconds=30 * i), lo, la, 10.0) for i, (lo, la) in enumerate(zip(lon, lat))]
        tracks.append((200000000 + v, rows))
    return tracks


def test_wkb_both_endians():
    assert _wkb_point(_blob(1.5, -2.25)) == (1.5, -2.25)
    assert _wkb_point(_blob(1.5, -2.25, big_endian=True)) == (1.5, -2.25)
    with pytest.raises(ValueError):
        _wkb_point(b"XX" + b"\x00" * 30)


def test_project_round_trip():
    x, y = project(*_km_to_lonlat([1.0, -2.0], [0.5, 1.5]), ORIGIN)
    np.testing.assert_allclose(x, [1.0, -2.0], atol=1e-9)
    np.testing.assert_allclose(y, [0.5, 1.5], atol=1e-9)


def test_extract_lines_recovers_tracks(tmp_path):
    tracks = _straight_tracks(n_vessels=6)
    path = tmp_path / "ais.gpkg"
    _write_gpkg(path, tracks)
    df = read_gpkg_points(path)
    assert len(df) == sum(len(r) for _, r in tracks)
    win = Window(-2.5, 2.5, -1.0, 1.5)
    lines = extract_lines(df, win, ORIGIN)
    assert len(lines) == 6
    assert (lines.linearity > 0.999).all()
    # each piece matches the generating line
    for _, row in lines.iterrows():
        k = int(row.mmsi) - 200000000
        rows = tracks[k][1]
        lon = np.array([r[1] for r in rows])
        lat = np.array([r[2] for r in rows])
        x, y = project(lon, lat, ORIGIN)
        resid = np.abs(x * np.cos(row.alpha) + y * np.sin(row.alpha) - row.p)
        assert resid.max() < 1e-6


def test_extract_lines_splits_turns_and_gaps(tmp_path):
    day = datetime(2017, 7, 5, 6)
    xs = np.concatenate([np.linspace(-2.0, 0.0, 30), np.zeros(30)])
    ys = np.concatenate([np.zeros(30), np.linspace(0.0, 1.2, 30)])
    lon, lat = _km_to_lonlat(xs, ys)
    rows = [(day + timedelta(seconds=20 * i), lo, la, 8.0) for i, (lo, la) in enumerate(zip(lon, lat))]
    # a second passage after a long gap, plus stationary reports that must be dropped
    xs2 = np.linspace(-2.0, 2.0, 30)
    lon2, lat2 = _km_to_lonlat(xs2, 0.8 * np.ones(30))
    rows += [
        (day + timedelta(hours=3, seconds=20 * i), lo, la, 8.0) for i, (lo, la) in enumerate(zip(lon2, lat2))
    ]
    rows += [(day + timedelta(hours=5, seconds=i), lon2[0], lat2[0], 0.0) for i in range(20)]
    path = tmp_path / "turn.gpkg"
    _write_gpkg(path, [(1, rows)])
    lines = extract_lines(read_gpkg_points(path), Window(-2.5, 2.5, -1.0, 1.5), ORIGIN)
    assert len(lines) == 3  # two legs of the turn + the later passage
    headings = sorted(np.round(canonicalize(lines.alpha.to_numpy(), lines.p.to_numpy())[0], 2))
    assert np.isclose(headings[0], 0.0, atol=0.05) or np.isclose(headings[-1], np.pi, atol=0.05)


def test_run_case_study_small(tmp_path):
    path = tmp_path / "ais.gpkg"
    _write_gpkg(path, _straight_tracks(n_vessels=40, seed=1))
    cfg = AISStudyConfig(
        epoch_hours=6.0,
        first_origin=2,
        n_sensors=2,
        candidate_spacing_km=0.5,
        grid_shape=(48, 32),
        lgcp_fit_shape=(24, 16),
        strategies=("pooled", "stacked", "lgcp", "hindsight", "fence", "random"),
        n_random=3,
    )
    res = run_case_study(path, tmp_path / "out", cfg)
    summ = pd.read_csv(tmp_path / "out" / "summary.csv")
    assert set(summ.strategy) == set(cfg.strategies)
    assert ((res.detection_rate >= 0) & (res.detection_rate <= 1)).all()
    lines = pd.read_csv(tmp_path / "out" / "lines.csv")
    assert "mmsi" not in lines.columns and "vessel" in lines.columns
    # hindsight plans on the test epoch itself, so it cannot lose to random
    s = summ.set_index("strategy")["mean_over_origins"]
    assert s["hindsight"] >= s["random"]


def test_passages_are_split_before_fitting_across_epoch_boundaries(tmp_path):
    tracks = _straight_tracks(n_vessels=1)
    start = datetime(2017, 7, 5, 2, 50)
    mmsi, rows = tracks[0]
    rows = [(start + timedelta(seconds=30 * i), lon, lat, sog) for i, (_, lon, lat, sog) in enumerate(rows)]
    path = tmp_path / "boundary.gpkg"
    _write_gpkg(path, [(mmsi, rows)])
    lines = extract_lines(read_gpkg_points(path), Window(-2.5, 2.5, -1.0, 1.5), ORIGIN, epoch_hours=3.0)
    assert len(lines) == 2
    assert (lines.start_time.dt.floor("3h") == lines.end_time.dt.floor("3h")).all()


def test_figures_smoke(tmp_path):
    from stochplace.figures import fig_legacy, fig_representation, label

    fig_representation(tmp_path)
    stats = fig_legacy(tmp_path)
    assert (tmp_path / "representation_space.png").exists()
    assert (tmp_path / "legacy_v01_check.png").exists()
    # v0.1 scored on the same future routes: uncertainty beats historical
    fut = stats["on_future_routes"]
    assert fut["uncertainty"] < fut["historical"]
    assert label("stacked:void").endswith("expected void obj.")


def test_figures_from_results(tmp_path):
    from stochplace.experiment import ExperimentConfig, run_experiment
    from stochplace.figures import fig_bound, fig_suite

    cfg = ExperimentConfig(
        name="suite_drift",
        scenario="drift",
        scenario_params={"speed": 0.3},
        history_epochs=5,
        seeds=2,
        n_sensors=2,
        grid={"n_alpha": 48, "n_p": 32},
        eval_grid={"n_alpha": 72, "n_p": 48},
        candidate_spacing=2.5,
        strategies=["pooled", "drift", "oracle"],
        forecast={"n_samples": 3},
    )
    run_experiment(cfg, tmp_path / "results" / "suite_drift", workers=1, progress=False)
    fig_suite(tmp_path / "results", tmp_path / "figs")
    stats = fig_bound(tmp_path / "results", tmp_path / "figs")
    assert stats["l1_plan_bound_holds"] == 1.0
    assert (tmp_path / "figs" / "scenario_suite.png").exists()


def test_five_hour_epochs_share_calendar_origin_before_and_after_fitting(tmp_path):
    tracks = _straight_tracks(n_vessels=1)
    start = datetime(2017, 7, 5, 4, 50)
    mmsi, rows = tracks[0]
    rows = [(start + timedelta(seconds=30 * i), lon, lat, sog) for i, (_, lon, lat, sog) in enumerate(rows)]
    path = tmp_path / "five-hour.gpkg"
    _write_gpkg(path, [(mmsi, rows)])
    points = read_gpkg_points(path)
    origin = points.time.min().normalize()
    lines = extract_lines(points, Window(-2.5, 2.5, -1.0, 1.5), ORIGIN, epoch_hours=5.0)
    assert len(lines) == 2
    start_epoch = (lines.start_time - origin).dt.total_seconds() // (5 * 3600)
    end_epoch = (lines.end_time - origin).dt.total_seconds() // (5 * 3600)
    assert (start_epoch == end_epoch).all()
    assert set(start_epoch) == {0, 1}
