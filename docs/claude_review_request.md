# Claude review request

Review this repository as an independent scientific and implementation audit.
Do not assume the previous Claude audit's conclusions are correct. The
previous audit was not fully independent; its PDF is a historical snapshot.

Start with `docs/part_b_review.md`, `docs/part_c_review.md`,
`docs/preregistration.md`, `docs/research_results.md` and `paper/main.pdf`.
Inspect implementation and raw artifacts, not just these narratives.

Check these specific questions:

1. Do both learned combiners still use valid component-sampling laws, with
   uncalibrated nonlinear objectives clearly disclosed? Learned weights are
   sampling probabilities, not established posterior model probabilities.
   A weighted sum is a proposed alternative law, not inherently calibrated.
2. Are AIS extraction, epoch assignment and independent verification anchored
   to the same raw-report calendar midnight, including non-divisor epochs?
3. Does a failed stacking solver use the actual held-out-score fallback and
   preserve the reason? Does TV search evaluate both starts under its own
   objective and retain the nominal feasible plan?
4. Are all original summaries preserved at absolute tolerance 1e-9, including
   corrected TV rows in the pre-C comparison? Verify the archived baselines.
5. Do the new scenarios, seeds, diagnostics and sampler gate follow the
   committed protocol? Both candidates fail; no sampler should be adopted.
   Distinguish latent expected-loss ranks from realized-count PIT.
6. Does AIS bandwidth selection use only earlier targets, including prefix
   bandwidth fits inside nested stacking validation? Inspect every origin
   and its weights; the reused day does not provide a fresh holdout.
7. Check the transport geometry, primal/dual agreement and concentrated-mass
   LP fixture. Are conditional certificates correctly separated from actual
   future performance and finite-grid outer-search optimality? Preserve the
   negative future-detection results.
8. Confirm that no multi-week AIS result or checksum is invented. C7 remains
   blocked, and defaults, old configs, seeds and legacy code are preserved.

Classify each finding as a confirmed defect, disclosure issue or proposed
method change. Give severity, exact file/line, evidence and a minimal fix.
Separate implementation validity, experimental evidence, calibration and
novelty. Report strengths only when directly supported. Do not describe the
project as publication-ready or calibrated merely because tests pass.

External Claude review has not yet been completed. The sign-in flow was
not completed in this session. Local checks and hosted CI are separate
records and must not be represented as Claude approval.
