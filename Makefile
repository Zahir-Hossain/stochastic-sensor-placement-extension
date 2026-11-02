.PHONY: install test test-all check lint typecheck experiments quick ais approx robustness figures tables paper all clean

PY ?= python

install:
	$(PY) -m pip install -e ".[dev,lint]"

test:
	$(PY) -m pytest -m "not slow and not octave"

test-all:
	$(PY) -m pytest --cov=stochplace --cov-report=term-missing

check:
	$(PY) scripts/check.py

lint:
	$(PY) -m ruff check src tests scripts examples
	$(PY) -m ruff format --check src tests scripts examples

typecheck:
	$(PY) -m mypy

experiments:
	stochplace run configs/suite_stationary.yaml configs/suite_drift.yaml \
	  configs/suite_lane_shift.yaml configs/suite_emergence.yaml \
	  configs/drift_sweep.yaml configs/data_scarcity.yaml --workers 2 --out results

quick:
	$(PY) scripts/reproduce.py --seeds 2 --workers 2 --skip-ais

ais:
	$(PY) scripts/fetch_ais_sample.py
	stochplace ais

approx:
	$(PY) scripts/approximation_study.py

robustness:
	stochplace robustness --workers 2

figures:
	stochplace figures --results results --out docs/figures

tables:
	$(PY) scripts/make_tables.py

paper:
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

all:
	$(PY) scripts/reproduce.py --in-place --workers 2 --paper

clean:
	$(PY) -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['.pytest_cache', '.mypy_cache', '.ruff_cache', '.hypothesis', 'htmlcov']]"
