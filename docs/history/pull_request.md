# Forecast-risk corrections and audit follow-up

Four original defects are corrected, C1-C6 outcomes are retained, and the
external Claude audit has been completed on snapshot 2c5fe28. The follow-up
adds solver-fit provenance, requires the shared AIS origin, broadens sample
calibration warnings, and corrects reporting scope.

No forecast, placement, calibration rule, seed or default is changed. Both
sampler candidates remain unadopted. The AIS probe's final-fit-only scope,
losses to individual components, boundary bandwidth selection, per-origin
variation, repeated plans and calibration-prefix limitations are explicit.

See docs/audit_followup.md for every finding and its resolution, numerical
comparisons, current checks and hosted CI evidence. The 118-test/nine-result
record belongs to the historical revision. C7 remains blocked by archive
access. Nothing in this document authorizes merging.
