# v0.1: the original MATLAB toy (June 2026)

This folder keeps the first version of the project exactly as it was,
so the history of the idea stays visible. The git tag `v0.1.0` points at
the repository state before the rebuild.

| File | What it is |
|---|---|
| `matlab/sensor_placement_simulation.m` | the original script, unchanged |
| `june-2026/Simulation_Results_June_2026.pdf` | the figures it produced |
| `methodology_v01.md` | the original methodology notes |

## Is the Python port faithful?

`stochplace.legacy` reimplements the script's numerical pipeline.
`tests/test_legacy_and_experiment.py::test_python_port_matches_original_matlab_script`
runs the **unchanged** `.m` file in GNU Octave (plotting calls are
stubbed out by `tests/octave/stubs/`), reads back the routes it generated
and the sensors it chose, and checks that the Python port picks exactly
the same sensors and reproduces the normalized miss scores to 12
significant digits. The CI workflow includes this check.

Octave's `rng(1)` stream differs from MATLAB's, so the specific numbers
differ from the June PDF; the comparison is made on identical routes.

## What v0.1 got right, and what it could not show

The idea (use predicted and uncertainty-expanded traffic, not only
history, when placing sensors) was sound. Three implementation choices
hid that:

1. **The intensity maps never reached the optimiser.** Greedy placement
   ran on the raw route lists; the maps were only plotted. Each map also
   had its own grid, so `lambda_E = w_H lambda_H + w_F lambda_F + w_U lambda_U`
   could not be formed.
2. **Each placement was scored on its own routes.** The historical
   placement was scored on historical routes, the uncertainty placement
   on the wider uncertainty routes, and so on. The uncertainty case looked
   worst simply because it was graded on a harder set.
3. **The budget was not binding.** Five sensors with range 1.5 on a narrow
   fan of lines detect about 99.99% of trajectories, so every method looks
   the same.

`docs/figures/legacy_v01_check.png` reruns v0.1 with the scoring fixed.
In v0.1 the "future" routes are the hand-shifted copy of the historical
routes, so the prediction placement was planned on exactly the routes it
is scored on; it plays the role of an oracle there.
Scored on the same future routes, the ranking flips: the uncertainty
placement misses fewer future trajectories than the historical one. With a
binding budget (2 sensors, range 0.5) the historical placement misses
about twice as many future trajectories as the prediction and uncertainty
placements. v2 builds on that observation.
