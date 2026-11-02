import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from stochplace.geometry import (
    Window,
    canonicalize,
    fit_line_tls,
    lines_to_rep,
    point_line_distance,
    rep_to_lines,
)

finite = st.floats(-50, 50, allow_nan=False, allow_infinity=False)
slopes = st.floats(-20, 20, allow_nan=False, allow_infinity=False)


@given(slopes, finite)
def test_round_trip(m, b):
    a, p = lines_to_rep(m, b)
    assert 0 < a < np.pi
    m2, b2 = rep_to_lines(a, p)
    assert np.isclose(m2, m, rtol=1e-9, atol=1e-9)
    assert np.isclose(b2, b, rtol=1e-9, atol=1e-7)


@given(slopes, finite, finite, finite)
def test_distance_identity(m, b, x, y):
    """|m x - y + b| / sqrt(1 + m^2) == |x cos(alpha) + y sin(alpha) - p|."""
    a, p = lines_to_rep(m, b)
    d_slope = abs(m * x - y + b) / np.sqrt(1 + m * m)
    d_rep = point_line_distance(x, y, a, p)
    assert np.isclose(d_rep, d_slope, rtol=1e-9, atol=1e-8)


@given(st.floats(-20, 20), finite)
def test_canonicalize_same_line(alpha, p):
    a, q = canonicalize(alpha, p)
    assert 0 <= a < np.pi
    # two points on the original line must lie on the canonical one
    for t in (-3.0, 4.0):
        x = p * np.cos(alpha) - t * np.sin(alpha)
        y = p * np.sin(alpha) + t * np.cos(alpha)
        assert abs(x * np.cos(a) + y * np.sin(a) - q) < 1e-7


def test_canonicalize_idempotent():
    rng = np.random.default_rng(0)
    a, p = canonicalize(rng.uniform(-10, 10, 100), rng.normal(size=100))
    a2, p2 = canonicalize(a, p)
    np.testing.assert_allclose(a, a2)
    np.testing.assert_allclose(p, p2)


@pytest.mark.parametrize("alpha,p", [(0.0, 2.0), (np.pi / 2, -1.0), (0.3, 0.5), (2.9, -4.0)])
def test_tls_recovers_line(alpha, p):
    t = np.linspace(-5, 5, 30)
    xy = np.column_stack([p * np.cos(alpha) - t * np.sin(alpha), p * np.sin(alpha) + t * np.cos(alpha)])
    a, q, lin = fit_line_tls(xy)
    a_true, p_true = canonicalize(alpha, p)
    assert lin > 0.999
    # compare as lines (allow the seam identification)
    d = min(abs(a - a_true) + abs(q - p_true), abs(abs(a - a_true) - np.pi) + abs(q + p_true))
    assert d < 1e-8


def test_tls_bad_input():
    with pytest.raises(ValueError):
        fit_line_tls(np.zeros((1, 2)))


def test_window_line_hits_matches_sampling():
    w = Window(-2, 3, -1, 1)
    rng = np.random.default_rng(1)
    a = rng.uniform(0, np.pi, 400)
    p = rng.uniform(-4, 4, 400)
    hits = w.line_hits(a, p)
    t = np.linspace(-20, 20, 4001)
    for ai, pi_, h in zip(a, p, hits):
        x = pi_ * np.cos(ai) - t * np.sin(ai)
        y = pi_ * np.sin(ai) + t * np.cos(ai)
        inside = np.any(w.contains(np.column_stack([x, y])))
        # sampling can only miss a hit that grazes a corner
        if inside:
            assert h
        if h and not inside:
            proj = w.corners @ np.array([np.cos(ai), np.sin(ai)])
            assert min(abs(proj - pi_)) < 0.05


def test_window_validation_and_grid():
    with pytest.raises(ValueError):
        Window(1, 0, 0, 1)
    w = Window(-10, 10, -5, 5)
    g = w.grid(1.0)
    assert g.shape == (21 * 11, 2)
    assert w.contains(g).all()
    assert np.isclose(w.p_bound, np.hypot(10, 5))


@settings(max_examples=50)
@given(st.floats(0, np.pi - 1e-6), st.floats(-3, 3))
def test_vertical_rep_to_lines_guard(alpha, p):
    if abs(np.sin(alpha)) < 1e-12:
        with pytest.raises(ValueError):
            rep_to_lines(alpha, p)
    else:
        rep_to_lines(alpha, p)
