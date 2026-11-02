# Part B validation

All four confirmed defects are corrected in separate commits. The frozen
pre-B checkpoint is recorded in `docs/part_b_baseline.json`.

The full regeneration changed only stacked-TV rows among the nine saved
CSV summaries; every other numeric entry is identical (absolute tolerance
1e-9, relative tolerance zero). All 360 TV-versus-nominal paired cases meet
or improve the nominal plan on the TV objective. The before/after table
is generated in `docs/tables/tv_before_after.md`. No stacking solver
fallbacks occurred in the six synthetic study families.

Full checks: 126 passed, one Octave parity test skipped locally because
Octave is absent. Ruff, formatting, mypy, example and artifact verification
passed. All ten result sets match source SHA-256
`c65951e3e348` (the full digest is in each result metadata file).
The rebuilt nine-page PDF was rendered and inspected for clipping and
layout. Raw logs and the machine-readable execution record are under
`docs/validation/part_b/`.

The first regeneration was interrupted with its session's Ctrl-C after
the four main suites finished, then the remaining studies were resumed
with eight workers. Settings and seeds were unchanged. The resume record
preserves this execution detail. No partial study result was retained.

This is the pre-C numerical baseline. New experimental features must
regenerate and match every original summary, including corrected TV rows,
without the Part B TV exception.
