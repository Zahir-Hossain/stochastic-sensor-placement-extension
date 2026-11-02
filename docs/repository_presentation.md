# Repository presentation and publication

The Python study is currently on `research-hardening` in
[draft PR #1](https://github.com/Zahir-Hossain/stochastic-sensor-placement-extension/pull/1).
The default `main` branch still shows the original June MATLAB version.
The following settings are proposals; they have not been applied.

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

1. Review the final diff and the CI results on the exact PR head.
2. Decide whether to mark the draft ready and merge it into `main`.
3. If merged, tag the actual merged commit and publish a release with the
   report. Version 2.1 is a working report version; no release tag is claimed.
4. Apply the About text/topics if desired. Renaming the repository to
   `stochplace` is optional and does not improve the scientific evidence.

The existing bundles must remain until an alternative preserves the original
baseline commits and a fresh clone passes the comparison commands. Deleting
them now would break that reproduction path.

The next research upgrade is the frozen multi-week AIS study. Neither an
alternate data source nor a new site should be substituted into that design
without documenting the change, checking its terms and fixing a fresh holdout.
