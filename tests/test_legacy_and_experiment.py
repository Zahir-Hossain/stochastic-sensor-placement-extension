import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stochplace.cli import main
from stochplace.experiment import ExperimentConfig, load_config, run_experiment, run_replicate
from stochplace.legacy import legacy_candidates, legacy_pipeline, legacy_routes

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_candidate_order():
    c = legacy_candidates()
    assert c.shape == (231, 2)
    # MATLAB column-major order: y runs fastest
    np.testing.assert_array_equal(c[:3], [[-10, -5], [-10, -4], [-10, -3]])
    np.testing.assert_array_equal(c[11], [-9, -5])


def test_legacy_pipeline_runs():
    s, b = legacy_routes(np.random.default_rng(1), n=60)
    r = legacy_pipeline(s, b, k=3)
    assert r.historical_sensors.shape == (3, 2)
    assert set(r.normalized_miss) == {"historical", "prediction", "uncertainty"}
    assert len(r.routes["uncertainty"][0]) == 9 * 2 * 60


@pytest.mark.octave
@pytest.mark.skipif(shutil.which("octave") is None, reason="GNU Octave not installed")
def test_python_port_matches_original_matlab_script(tmp_path):
    """Run the *unchanged* v0.1 .m file in Octave and compare with the port."""
    script = ROOT / "tests" / "octave" / "run_legacy.m"
    env = {
        "LEGACY_DIR": str(ROOT / "legacy" / "matlab"),
        "STUB_DIR": str(ROOT / "tests" / "octave" / "stubs"),
        "OUT_DIR": str(tmp_path),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(tmp_path),
    }
    subprocess.run(
        ["octave", "--no-gui", "--quiet", "--no-window-system", str(script)],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        timeout=900,
    )
    slope = np.loadtxt(tmp_path / "slope.csv")
    intercept = np.loadtxt(tmp_path / "intercept.csv")
    r = legacy_pipeline(slope, intercept)
    for attr, fname in [
        ("historical_sensors", "hist_sensors.csv"),
        ("future_sensors", "future_sensors.csv"),
        ("uncertainty_sensors", "unc_sensors.csv"),
    ]:
        np.testing.assert_array_equal(getattr(r, attr), np.loadtxt(tmp_path / fname, delimiter=","))
    scores = np.loadtxt(tmp_path / "scores.csv", delimiter=",")
    np.testing.assert_allclose(
        [r.normalized_miss[k] for k in ("historical", "prediction", "uncertainty")], scores, rtol=1e-12
    )


def _tiny_cfg(**kw):
    base = dict(
        name="tiny",
        scenario="drift",
        sweep={"speed": [0.3]},
        history_epochs=5,
        seeds=2,
        n_sensors=3,
        grid={"n_alpha": 60, "n_p": 32},
        eval_grid={"n_alpha": 90, "n_p": 48},
        lgcp_fit_shape=[30, 16],
        candidate_spacing=2.0,
        strategies=["pooled", "drift_u", "drift_u:cvar", "lgcp", "oracle", "fence", "random"],
        forecast={"n_samples": 4},
    )
    base.update(kw)
    return ExperimentConfig(**base)


def test_replicate_and_regret_bound():
    rows = run_replicate(_tiny_cfg(), {"speed": 0.3}, 0, 2, 0)
    df = pd.DataFrame(rows)
    o = df[df.strategy == "oracle"].iloc[0]
    assert o.gap_pp == 0 and o.regret_plan == 0
    planned = df.dropna(subset=["l1_plan"])
    # Proposition 1: regret <= max(delta, 0) + ||lambda - mu||_1
    bound = planned.delta_plan.clip(lower=0) + planned.l1_plan
    assert (planned.regret_plan <= bound + 1e-9).all()
    # Proposition 1b: the coverage-weighted error is a tighter valid bound
    tight = planned.delta_plan.clip(lower=0) + planned.l1_cov_plan
    assert (planned.regret_plan <= tight + 1e-9).all()
    assert (planned.l1_cov_plan <= planned.l1_plan + 1e-9).all()
    assert ((df.detection_rate >= 0) & (df.detection_rate <= 1)).all()


def test_run_experiment_and_cli(tmp_path):
    out = run_experiment(
        _tiny_cfg(strategies=["pooled", "drift", "oracle"]), tmp_path / "e", workers=1, progress=False
    )
    for f in ("runs.csv", "summary.csv", "meta.json"):
        assert (out / f).exists()
    summ = pd.read_csv(out / "summary.csv")
    assert set(summ.strategy) == {"pooled", "drift", "oracle"}
    assert "gain_vs_baseline_pp" in summ.columns
    assert main(["legacy", "--seed", "3"]) == 0
    with pytest.raises(SystemExit):
        main(["--version"])


@pytest.mark.parametrize("path", sorted((ROOT / "configs").glob("*.yaml")))
def test_configs_parse(path):
    cfg = load_config(path)
    assert cfg.seeds > 0 and cfg.strategies
    assert len(cfg.settings()) >= 1
