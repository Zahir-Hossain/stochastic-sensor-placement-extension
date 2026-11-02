"""Sensor detection models.

A sensor at ``(x_s, y_s)`` detects a straight trajectory ``(alpha, p)``
with a probability that depends only on the perpendicular distance

    d = | x_s cos(alpha) + y_s sin(alpha) - p |.

Sensors are assumed to detect independently, so the probability that a
network ``S`` misses a trajectory is ``prod_{s in S} (1 - P_D(d_s))``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Protocol

import numpy as np

from ._typing import FloatArray

__all__ = ["DiskSensor", "GaussianSensor", "LogisticSensor", "SensorModel", "sensor_from_config"]


class SensorModel(Protocol):
    """Interface for distance-based detection models."""

    @property
    def smooth(self) -> bool:
        """Whether :meth:`prob` is differentiable (enables refinement)."""
        ...

    def prob(self, d2: FloatArray) -> FloatArray:
        """Detection probability as a function of squared distance."""
        ...

    def dprob_dd2(self, d2: FloatArray) -> FloatArray:
        """Derivative of :meth:`prob` with respect to squared distance."""
        ...


@dataclass(frozen=True)
class GaussianSensor:
    """``P_D = rho * exp(-d^2 / (2 r^2))`` (the model of the original toy)."""

    rho: float = 0.95
    r: float = 1.5
    smooth: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if not (0 < self.rho <= 1):
            raise ValueError("rho must be in (0, 1]")
        if self.r <= 0:
            raise ValueError("r must be positive")

    def prob(self, d2: FloatArray) -> FloatArray:
        return self.rho * np.exp(-np.asarray(d2) / (2 * self.r**2))

    def dprob_dd2(self, d2: FloatArray) -> FloatArray:
        return -self.prob(d2) / (2 * self.r**2)


@dataclass(frozen=True)
class LogisticSensor:
    """Smooth step: ``P_D = rho / (1 + exp((d - R) / s))``."""

    rho: float = 0.95
    R: float = 1.5
    s: float = 0.2
    smooth: ClassVar[bool] = True

    def prob(self, d2: FloatArray) -> FloatArray:
        d = np.sqrt(np.asarray(d2))
        return self.rho / (1.0 + np.exp((d - self.R) / self.s))

    def dprob_dd2(self, d2: FloatArray) -> FloatArray:
        d = np.sqrt(np.maximum(np.asarray(d2), 1e-24))
        e = np.exp((d - self.R) / self.s)
        dp_dd = -self.rho * e / (self.s * (1 + e) ** 2)
        return dp_dd / (2 * d)


@dataclass(frozen=True)
class DiskSensor:
    """Binary range: ``P_D = rho`` if ``d <= R`` else 0. Not differentiable."""

    rho: float = 0.95
    R: float = 1.5
    smooth: ClassVar[bool] = False

    def prob(self, d2: FloatArray) -> FloatArray:
        return np.where(np.asarray(d2) <= self.R**2, self.rho, 0.0)

    def dprob_dd2(self, d2: FloatArray) -> FloatArray:
        return np.zeros_like(np.asarray(d2, dtype=float))


def sensor_from_config(cfg: dict[str, object]) -> SensorModel:
    """Build a sensor model from ``{"type": ..., **params}``."""
    kind = str(cfg.get("type", "gaussian")).lower()
    params = {k: float(v) for k, v in cfg.items() if k != "type"}  # type: ignore[arg-type]
    if kind == "gaussian":
        return GaussianSensor(**params)
    if kind == "logistic":
        return LogisticSensor(**params)
    if kind == "disk":
        return DiskSensor(**params)
    raise ValueError(f"unknown sensor type {kind!r}")
