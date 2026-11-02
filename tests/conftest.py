import numpy as np
import pytest

from stochplace import GaussianSensor, RepGrid, Window, make_scenario


@pytest.fixture
def window():
    return Window(-10.0, 10.0, -5.0, 5.0)


@pytest.fixture
def grid(window):
    return RepGrid(window, 90, 48)


@pytest.fixture
def small_grid():
    return RepGrid(Window(-4.0, 4.0, -2.0, 2.0), 36, 24)


@pytest.fixture
def sensor():
    return GaussianSensor(0.95, 1.0)


@pytest.fixture
def rng():
    return np.random.default_rng(2024)


@pytest.fixture
def drift_scenario():
    return make_scenario("drift", speed=0.3)
