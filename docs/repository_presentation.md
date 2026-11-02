# Repository presentation and publication

The Python study was merged into `main` through
[PR #1](https://github.com/Zahir-Hossain/stochastic-sensor-placement-extension/pull/1)
on 2 November 2026 (merge commit `308afae`). The repository settings below
are proposals; they have not been applied.

## Proposed About text

Reproducible Python study of sensor placement under shifting traffic:
chronological intensity stacking, risk objectives and ambiguity sets,
with synthetic stress tests, public AIS tracks and reported failures.

## Proposed topics

`sensor-placement`, `barrier-coverage`, `point-processes`, `forecasting`,
`distributionally-robust-optimization`, `optimal-transport`, `ais`,
`maritime`, `python`, `reproducible-research`.

The current overview figure is `docs/figures/research_overview.png`.
It shows a successful designed case next to reversal, component and AIS losses.

## Publication sequence

1. Done: PR #1 was reviewed, passed all eight CI jobs on its exact head
   `fffd5d0`, and was merged as `308afae`.
2. Replace the About text, which still describes the June MATLAB toy, and
   apply the topics above.
3. Tag the June MATLAB version and the merged study, then publish a release
   with `paper/main.pdf`:

   ```bash
   git tag v0.1.0 b67f3a5
   git tag v2.1.0 308afae
   git push origin v0.1.0 v2.1.0
   ```

   Until this is done, no version tag or release exists.
4. Renaming the repository to `stochplace` is optional and does not improve
   the scientific evidence.

The existing bundles must remain until an alternative preserves the original
baseline commits and a fresh clone passes the comparison commands. Deleting
them now would break that reproduction path.

The next research upgrade is the frozen multi-week AIS study. Neither an
alternate data source nor a new site should be substituted into that design
without documenting the change, checking its terms and fixing a fresh holdout.
