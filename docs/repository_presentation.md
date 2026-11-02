# Repository presentation and publication

The Python study was merged into `main` through
[PR #1](https://github.com/Zahir-Hossain/stochastic-sensor-placement-extension/pull/1)
on 2 November 2026 (merge commit `308afae`), followed by
[PR #2](https://github.com/Zahir-Hossain/stochastic-sensor-placement-extension/pull/2)
and [PR #3](https://github.com/Zahir-Hossain/stochastic-sensor-placement-extension/pull/3).

## Applied on 2 November 2026

About text:

> Where should fixed sensors go when traffic shifts? Python package and stress
> tests of forecast-aware placement: wins when the forecast is right, losses
> when it is not, on synthetic traffic and real AIS ship tracks.

Topics: `ais`, `barrier-coverage`, `distributionally-robust-optimization`,
`forecasting`, `maritime`, `optimal-transport`, `point-processes`,
`probabilistic-modeling`, `python`, `reproducible-research`,
`scientific-computing`, `sensor-networks`, `sensor-placement`,
`stochastic-systems`, `trajectory-prediction`, `uncertainty`.

Social preview: `docs/figures/social_preview.png`, rendered with the README
animation by `scripts/make_animation.py`.

Release: [v2.1.0](https://github.com/Zahir-Hossain/stochastic-sensor-placement-extension/releases/tag/v2.1.0),
tag at `1d32aa9`, with the technical report attached.

The June 2026 MATLAB version remains in `legacy/` and at commit `b67f3a5`;
it has no tag.

## Not done

Renaming the repository to `stochplace` is optional and does not improve the
scientific evidence.

The existing bundles must remain until an alternative preserves the original
baseline commits and a fresh clone passes the comparison commands. Deleting
them now would break that reproduction path.

The next research upgrade is the frozen multi-week AIS study. Neither an
alternate data source nor a new site should be substituted into that design
without documenting the change, checking its terms and fixing a fresh holdout.
