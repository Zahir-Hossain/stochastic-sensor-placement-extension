# Execution notes

The first C preflight exposed specialized YAML files in the ordinary
experiment-config directory. They were moved to configs/research without
changing their values, and all checks were rerun.

A suspended session ended during AIS bandwidth sensitivity after the
original synthetic study results had been written. Remaining baseline
steps were resumed with identical settings. Full C1-C6 outcomes were then
run from frozen configs and candidates.

The first transport calibration LP falsely reported infeasibility for
concentrated probability masses. Reproduced on stationary seed 0, target
5; disabling presolve and tightening primal/dual feasibility to 1e-10
solved the original constraints. No mass was discarded. The fixture is
in tests/fixtures/concentrated_transport.npz. All C5 runs were rerun; the
initial failure log is retained.

The original report figure population is explicitly scoped to its ten
study folders to avoid mixing partially written research folders.
Scientific comparison tolerance remains absolute 1e-9, relative zero.

## Later audit clarification

Before the first C1/C3 outcome run, commit a98aaad corrected the sampler
runner to construct the sensor from the frozen config (r=1.0), instead of
GaussianSensor() with default r=1.5. No frozen parameter changed. This
implementation defect was bundled under a disclosure-labelled commit and
was omitted from the initial execution notes; this paragraph records that
omission after the external audit. Local commit order supports the stated
sequence, but there was no external preregistration timestamp.
