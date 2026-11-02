"""stochplace: sensor placement for stochastic line trajectories under traffic shift.

Builds on the barrier-coverage framework of Kim, Stilwell, Yetkin and
Jimenez (arXiv:2505.00825): trajectories live in the ``(alpha, p)``
line representation space, their intensity is estimated there, and
sensors are placed to maximise the void probability of undetected
trajectories. This package adds forecasting of how that intensity
shifts over time, objectives over forecast uncertainty, and an
evaluation protocol that scores placements on the realised future.
"""

from .evaluate import Score, bootstrap_ci, score_on_lines, score_on_truth
from .forecast import FORECASTERS, ForecastConfig, forecast
from .geometry import Window, canonicalize, fit_line_tls, lines_to_rep, point_line_distance, rep_to_lines
from .grid import IntensityField, RepGrid
from .intensity import kde_intensity, lgcp_intensity
from .objective import Problem, miss_probability_lines
from .optimize import (
    Placement,
    brute_force,
    fence_placement,
    greedy,
    random_placement,
    refine,
    solve,
    swap_refine,
)
from .risk import AdversarialMass, cvar_weights, tv_adversary, tv_values
from .scenarios import Lane, Scenario, make_scenario
from .sensors import DiskSensor, GaussianSensor, LogisticSensor

__version__ = "2.1.0"

__all__ = [
    "FORECASTERS",
    "AdversarialMass",
    "DiskSensor",
    "ForecastConfig",
    "GaussianSensor",
    "IntensityField",
    "Lane",
    "LogisticSensor",
    "Placement",
    "Problem",
    "RepGrid",
    "Scenario",
    "Score",
    "Window",
    "__version__",
    "bootstrap_ci",
    "brute_force",
    "canonicalize",
    "cvar_weights",
    "fence_placement",
    "fit_line_tls",
    "forecast",
    "greedy",
    "kde_intensity",
    "lgcp_intensity",
    "lines_to_rep",
    "make_scenario",
    "miss_probability_lines",
    "point_line_distance",
    "random_placement",
    "refine",
    "rep_to_lines",
    "score_on_lines",
    "score_on_truth",
    "solve",
    "swap_refine",
    "tv_adversary",
    "tv_values",
]
