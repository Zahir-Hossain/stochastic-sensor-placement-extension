# External audit follow-up

Claude Opus 5.5 Extra audited published snapshot
`2c5fe28f46f0b8e748784680f5fcc1517edcb92a`. The full captured report and
its provenance are under [archived Claude audit](history/validation/claude/). It found
no result-changing implementation defect. Its claims about tests and
regeneration are external-review evidence, distinct from the checks below.

## Resolutions

| Finding | Action | Classification |
|---|---|---|
| D1 | Keep the original AIS probe, explicitly label its final-fit-only scaling and default-bandwidth backtests, and distinguish the C4 nested-prefix result | Disclosure |
| D2 | Generate every C1 strategy's detection and paired comparisons, including losses to single components; preserve the primary pooled-history contrast | Disclosure |
| D3 | Record fit status and failure reason in the four reviewed runners, plus residual/transport calibration-prefix fit records; say not recorded when a counter lacks data | Confirmed defect |
| D4 | Require the raw-report epoch origin explicitly; remove the unused guess from the first retained line | Confirmed latent defect |
| D5 | Qualify freeze evidence as local commit order with no external timestamp; document the pre-outcome sensor-config correction and its earlier omission | Disclosure |
| D6 | Mark old validation records as archived and replace current review pointers | Disclosure |
| D7/D9 | Report the lower-grid-edge selections and all four trained-history-versus-stacking differences; qualify the mean by the influential origin | Disclosure |
| D8 | Record full C5 sensor plans, show distinct plan counts, and mark zero-width intervals as degenerate | Disclosure |
| D10 | State that the repository's original primal/dual check uses four-cell unit fixtures; retain the external audit's larger check as separate evidence | Disclosure |
| D11 | State that fixed sampler streams are reused across history seeds; no claim of independent Monte Carlo sampler draws | Disclosure |
| D12 | Extend the runtime warning to every sample-bearing nonlinear-risk field | Confirmed warning gap |
| D13 | Attribute the established Wasserstein construction and prior robust coverage control using verified primary publications | Disclosure |
| D14 | Save exact-head CI metadata and captured-log digests; add baseline comparisons, deterministic report generation and research smoke checks to CI | Confirmed validation gap |
| P2 | Explain that the first calibration prefix returns pooled history and can determine the radius; generate its contribution and radius/truth-distance diagnostics without changing the rule | Disclosure; method change deferred |
| P3 | Check the concentrated-mass fixture against a frozen reference independently calculated with POT 0.9.7.post1 network simplex; no POT dependency is needed to run tests | Validation improvement |

P1 and P4 would change the fallback choice or sampler randomness. They are
not adopted. Changing the calibration rule in P2 would be a new experiment
with a new frozen design and fresh evaluation, not a repair of these outcomes.
The sampler gates, bandwidth grid, calibration quantile, configurations,
seeds, prediction rules and all previous negative results are retained.
Secondary component comparisons added after the audit are explicitly
descriptive and do not replace the frozen primary metric.

The external audit used 20,000 bootstrap resamples for its extra component
comparisons. The repository keeps its existing fixed bootstrap procedure.
Under that procedure the random-walk versus recent interval includes zero
(the rounded upper endpoint is +0.01 pp), so the audit's near-zero negative
endpoint is not adopted as evidence of a clear loss. The two large trend
losses remain visible. All generated intervals come from the saved runs.

## Validation

The follow-up changes package-source bytes, so all 19 source-dependent
result sets are regenerated. Comparison with the audited snapshot enforces
absolute tolerance 1e-9 and relative tolerance zero for every saved CSV
summary; the historical pre-C check is also retained. A final execution
record and comparison logs are saved under docs/history/validation/audit_followup.

Final local result: **158 tests passed, one Octave test skipped locally**;
lint, formatting, mypy, example, nineteen-set verification, eighteen-summary
comparison, deterministic generators and both research smoke commands pass.
All eighteen CSV summaries have maximum absolute difference zero. The
rebuilt fourteen-page report has been rendered and visually checked.
The machine record is [validation.json](history/validation/audit_followup/validation.json).

The original hosted CI record is now tied explicitly to head
`2c5fe28f46f0b8e748784680f5fcc1517edcb92a`, event pull_request, run
41368309735, conclusion success. Eight job-log hashes are retained in
[hosted_ci_2c5fe28.json](history/validation/claude/hosted_ci_2c5fe28.json). These
are hashes of decoded UTF-8 logs captured from the connector. Updated
head CI is reported separately in the PR and delivery record.

C7 remains an external-data dependency; no multi-week outcome or checksum
is claimed. The draft PR has not been merged. Green tests and the external
audit establish neither calibrated uncertainty nor publication-level novelty.
