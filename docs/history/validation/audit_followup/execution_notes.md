# Audit follow-up execution

All nineteen result sets were regenerated after the package-source logging,
warning and explicit-origin fixes. Every one of the eighteen saved CSV
summaries matches audited snapshot 2c5fe28 exactly under atol 1e-9, rtol 0.
The nine original pre-C summaries also match.

The initial final verifier exposed a pandas edge case: an empty failure-
message column was inferred as float, so the .str accessor failed even
with no solver failures. The corrected string conversion has both a
nonfailure and a missing-failure-reason regression case. All four research
sets were regenerated again because their helper fingerprint changed.
C3 used seven workers alongside single-worker AIS controls. The remaining
one-worker C5 invocation was stopped with its session Ctrl-C (exit 130)
and restarted with eight workers when the other study finished. No
partial output was retained; settings and seeds were unchanged.

A truncated local test log was retained in output; the final full check
was repeated to obtain the complete human-readable log and machine record.
A clean report rebuild removed empty generated auxiliary caches; the PDF
remains fourteen pages with no overfull boxes. New component tables and
all appendix pages were visually checked. The logged smoke commands ran
with separate output folders. Generator hashes were identical before
and after repeating the exact render-only commands used by CI.
