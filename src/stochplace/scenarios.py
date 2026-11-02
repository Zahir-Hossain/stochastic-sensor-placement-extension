"""Synthetic traffic with a known, time-varying ground-truth intensity.

Traffic is a mixture of Gaussian *lanes* in representation space. Lane
``k`` has centre ``mu_k(t) = mu_k(0) + v_k t`` and traffic share
``pi_k(t) = softmax(l_k + s_k t)``. In epoch ``t`` the number of lines is
Poisson with mean ``rate``, so the true per-epoch intensity is

    lambda_t(alpha, p) = rate * sum_k pi_k(t) N((alpha, p); mu_k(t), diag(sd_k^2)).

Because the truth is known in closed form, any placement can be scored
exactly against the *realised future*, not against the data it was
planned on.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.special import ndtr

from ._typing import FloatArray
from .geometry import Window, canonicalize, lines_to_rep
from .grid import IntensityField, RepGrid

__all__ = ["SCENARIOS", "Lane", "Scenario", "make_scenario"]


@dataclass(frozen=True)
class Lane:
    """One Gaussian traffic lane in ``(alpha, p)``.

    Use :meth:`from_slope` to specify the lane by a slope/intercept centre.
    """

    alpha: float
    p: float
    sd_alpha: float
    sd_p: float
    v_alpha: float = 0.0
    v_p: float = 0.0
    logit: float = 0.0
    logit_slope: float = 0.0
    turn_time: float | None = None

    @staticmethod
    def from_slope(
        slope: float,
        intercept: float,
        sd_alpha: float,
        sd_p: float,
        **kw: float,
    ) -> Lane:
        a, p = lines_to_rep(slope, intercept)
        return Lane(float(a), float(p), sd_alpha, sd_p, **kw)

    def centre(self, t: float) -> tuple[float, float]:
        elapsed = t if self.turn_time is None or t <= self.turn_time else 2 * self.turn_time - t
        return self.alpha + self.v_alpha * elapsed, self.p + self.v_p * elapsed


@dataclass
class Scenario:
    """Time-varying lane mixture inside a sensor window."""

    name: str
    lanes: list[Lane]
    window: Window
    rate: float = 120.0
    description: str = ""
    meta: dict[str, object] = field(default_factory=dict)

    def weights(self, t: float) -> FloatArray:
        z = np.array([ln.logit + ln.logit_slope * t for ln in self.lanes])
        z = z - z.max()
        w = np.exp(z)
        return w / w.sum()

    # ------------------------------------------------------------------
    def truth(self, grid: RepGrid, t: float) -> IntensityField:
        """Exact per-epoch intensity at time ``t`` on ``grid`` (cell-integrated)."""
        ae, pe = grid.alpha_edges, grid.p_edges
        mass = np.zeros(grid.shape)
        for w, ln in zip(self.weights(t), self.lanes):
            ca, cp = (float(v) for v in canonicalize(*ln.centre(t)))
            for shift, sign in ((0.0, 1.0), (-np.pi, -1.0), (np.pi, -1.0)):
                u = np.diff(ndtr((ae - (ca + shift)) / ln.sd_alpha))
                v = np.diff(ndtr((pe - sign * cp) / ln.sd_p))
                mass += w * np.outer(u, v)
        dens = self.rate * mass / grid.cell_area
        return IntensityField(grid, dens, label=f"truth@t={t:g}")

    def sample(
        self, t: float, rng: np.random.Generator, n: int | None = None
    ) -> tuple[FloatArray, FloatArray]:
        """Draw the lines of one epoch, keeping only lines that hit the window."""
        n = int(rng.poisson(self.rate)) if n is None else n
        if n == 0:
            return np.empty(0), np.empty(0)
        comp = rng.choice(len(self.lanes), size=n, p=self.weights(t))
        a = np.empty(n)
        p = np.empty(n)
        for k, ln in enumerate(self.lanes):
            idx = comp == k
            ca, cp = ln.centre(t)
            a[idx] = ca + ln.sd_alpha * rng.standard_normal(idx.sum())
            p[idx] = cp + ln.sd_p * rng.standard_normal(idx.sum())
        a, p = canonicalize(a, p)
        keep = self.window.line_hits(a, p)
        return a[keep], p[keep]

    def history(self, n_epochs: int, rng: np.random.Generator) -> list[tuple[FloatArray, FloatArray]]:
        """Observed epochs ``t = 0 .. n_epochs - 1``."""
        return [self.sample(t, rng) for t in range(n_epochs)]

    def with_rate(self, rate: float) -> Scenario:
        return Scenario(self.name, self.lanes, self.window, rate, self.description, dict(self.meta))


# ----------------------------------------------------------------------
# Scenario library
# ----------------------------------------------------------------------

DEFAULT_WINDOW = Window(-10.0, 10.0, -5.0, 5.0)

# Lane centred on the original MATLAB toy (slope 0.2, intercept 0) but with
# a wider offset spread, so that a 4-sensor budget cannot cover everything
# and placement decisions matter.
_BASE_ALPHA, _BASE_P = (float(v) for v in lines_to_rep(0.2, 0.0))
_BASE_SDA = 0.05
_BASE_SDP = 1.2


def _drift(speed: float = 0.25, rate: float = 120.0) -> Scenario:
    """One lane whose heading and offset drift steadily.

    ``speed`` is the offset drift in window units per epoch; the heading
    rotates by ``0.02 * speed / 0.25`` rad per epoch. ``speed=0.25`` over
    two epochs is close to the hand-set future shift of the original toy
    (slope +0.05, intercept +0.5).
    """
    lane = Lane(
        _BASE_ALPHA,
        _BASE_P,
        _BASE_SDA,
        _BASE_SDP,
        v_alpha=0.02 * speed / 0.25,
        v_p=speed,
    )
    return Scenario(
        "drift",
        [lane],
        DEFAULT_WINDOW,
        rate,
        "Single lane drifting in heading and offset.",
        {"speed": speed},
    )


def _lane_shift(rate: float = 120.0, rate_of_change: float = 0.45) -> Scenario:
    """Traffic share moves from lane A to lane B over time."""
    a = Lane.from_slope(0.15, -2.5, 0.05, 0.8, logit=1.6, logit_slope=-rate_of_change)
    b = Lane.from_slope(-0.25, 2.5, 0.05, 0.8, logit=-1.6, logit_slope=rate_of_change)
    return Scenario(
        "lane_shift",
        [a, b],
        DEFAULT_WINDOW,
        rate,
        "Two fixed lanes; share moves from A to B.",
        {"rate_of_change": rate_of_change},
    )


def _emergence(rate: float = 120.0) -> Scenario:
    """A third lane appears late in the history and grows fast."""
    a = Lane.from_slope(0.2, -1.5, 0.05, 0.8, logit=0.0)
    b = Lane.from_slope(-0.1, 3.0, 0.05, 0.8, logit=-0.3)
    c = Lane.from_slope(0.6, -3.0, 0.05, 0.8, logit=-7.0, logit_slope=0.9)
    return Scenario(
        "emergence",
        [a, b, c],
        DEFAULT_WINDOW,
        rate,
        "Two stable lanes plus a new lane that only starts to show near the end of the history.",
    )


def _stationary(rate: float = 120.0) -> Scenario:
    a = Lane.from_slope(0.2, -1.5, 0.05, 1.0, logit=0.3)
    b = Lane.from_slope(-0.3, 2.0, 0.05, 1.0, logit=0.0)
    return Scenario("stationary", [a, b], DEFAULT_WINDOW, rate, "Two lanes, no change over time.")


def _reversal(speed: float = 0.3, rate: float = 120.0, turn_time: float = 7.0) -> Scenario:
    """An unannounced drift reversal just after the default history ends."""
    lane = Lane(
        _BASE_ALPHA, _BASE_P, _BASE_SDA, _BASE_SDP, v_alpha=0.08 * speed, v_p=speed, turn_time=turn_time
    )
    return Scenario(
        "reversal",
        [lane],
        DEFAULT_WINDOW,
        rate,
        "Drift reverses at the end of training; no forecaster is told.",
        {"speed": speed, "turn_time": turn_time},
    )


def _seam_drift(rate: float = 120.0, speed: float = 0.025) -> Scenario:
    """A near-vertical lane crosses the alpha=0/pi representation seam."""
    lane = Lane(0.08, 0.5, 0.025, 0.9, v_alpha=-speed, v_p=0.02)
    return Scenario(
        "seam_drift",
        [lane],
        DEFAULT_WINDOW,
        rate,
        "Near-vertical lane crossing the Moebius seam.",
        {"speed": speed},
    )


@dataclass(frozen=True)
class _ResearchLane(Lane):
    """Nonlinear centres used only by the preregistered holdout scenarios."""

    motion: str = "accelerating"
    offsets: tuple[float, ...] = ()
    switch_epoch: int = 9

    def centre(self, t: float) -> tuple[float, float]:
        if self.motion == "accelerating":
            return self.alpha + 0.008 * t + 0.001 * t**2, self.p + 0.1 * t + 0.03 * t**2
        if self.motion == "rotating_quadratic":
            return self.alpha + 0.05 * t, self.p + 0.04 * t**2
        if self.motion == "random_walk":
            offset = np.interp(t, np.arange(len(self.offsets)), self.offsets)
            return self.alpha, self.p + float(offset)
        if self.motion == "random_switch":
            return self.alpha, self.p + (2.5 if t >= self.switch_epoch else 0.0)
        if self.motion == "lane_split":
            return self.alpha, self.p + self.v_p * max(t - 5.0, 0.0)
        raise ValueError(f"unknown research motion {self.motion!r}")


def _research_scenario(motion: str, scenario_seed: float = 0, rate: float = 120.0) -> Scenario:
    seed = int(scenario_seed)
    offsets: tuple[float, ...] = ()
    switch = 9
    if motion == "random_walk":
        rng = np.random.default_rng([seed, 314159])
        offsets = tuple(np.r_[0.0, np.cumsum(rng.normal(0.0, 0.45, 63))].tolist())
    elif motion == "random_switch":
        switch = int(np.random.default_rng([seed, 271828]).integers(4, 10))
    lane = _ResearchLane(
        _BASE_ALPHA,
        _BASE_P,
        _BASE_SDA,
        _BASE_SDP,
        motion=motion,
        offsets=offsets,
        switch_epoch=switch,
    )
    lanes: list[Lane] = [lane]
    if motion == "lane_split":
        lanes = [
            _ResearchLane(_BASE_ALPHA, _BASE_P, _BASE_SDA, _BASE_SDP, v_p=sign * 0.65, motion=motion)
            for sign in (-1, 1)
        ]
    return Scenario(
        motion,
        lanes,
        DEFAULT_WINDOW,
        rate,
        "Preregistered shift outside the candidate motion families.",
        {"scenario_seed": seed, "protocol": "docs/preregistration.md"},
    )


def _accelerating(scenario_seed: float = 0, rate: float = 120.0) -> Scenario:
    return _research_scenario("accelerating", scenario_seed, rate)


def _rotating_quadratic(scenario_seed: float = 0, rate: float = 120.0) -> Scenario:
    return _research_scenario("rotating_quadratic", scenario_seed, rate)


def _random_walk(scenario_seed: float = 0, rate: float = 120.0) -> Scenario:
    return _research_scenario("random_walk", scenario_seed, rate)


def _random_switch(scenario_seed: float = 0, rate: float = 120.0) -> Scenario:
    return _research_scenario("random_switch", scenario_seed, rate)


def _lane_split(scenario_seed: float = 0, rate: float = 120.0) -> Scenario:
    return _research_scenario("lane_split", scenario_seed, rate)


SCENARIOS = {
    "drift": _drift,
    "lane_shift": _lane_shift,
    "emergence": _emergence,
    "stationary": _stationary,
    "reversal": _reversal,
    "seam_drift": _seam_drift,
    "accelerating": _accelerating,
    "rotating_quadratic": _rotating_quadratic,
    "random_walk": _random_walk,
    "random_switch": _random_switch,
    "lane_split": _lane_split,
}


def make_scenario(name: str, **kw: float) -> Scenario:
    """Build a named scenario, e.g. ``make_scenario("drift", speed=0.4)``."""
    if name not in SCENARIOS:
        raise KeyError(f"unknown scenario {name!r}; choose from {sorted(SCENARIOS)}")
    return SCENARIOS[name](**kw)  # type: ignore[operator]
