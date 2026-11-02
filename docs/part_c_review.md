# Part C validation and remaining dependencies

C1-C6 are implemented and reproduced. The preregistration and candidate
laws were committed before the new outcomes. All original configurations,
seeds and defaults remain intact. Every one of the nine original CSV
summaries matches the corrected pre-C checkpoint 3b8548d exactly; the
comparison enforces absolute tolerance 1e-9 and relative tolerance zero.

All 19 result sets verify against source fingerprint e8ff34cb65c4. This
includes 1,400 new shift-study rows, 600 sampler diagnostics, 12
training-selected AIS rows, 32 AIS ablation rows and 480 transport rows.
Raw results, configs, helper fingerprints and summary recomputation are
retained. The frozen sampler gate rejects both candidates; neither is
adopted. The generated research results prominently retain AIS and
transport limitations, including results that weaken the forecast claim.

Full local validation: 152 tests passed and one Octave parity test was
skipped because Octave is unavailable. Lint, formatting, mypy, example,
artifact verification and summary comparison passed. The 12-page PDF was
rendered and checked, including all three new appendix pages. Local
validation is distinct from hosted CI and external Claude review.

The complete generated evidence is in research_results.md and the report
appendix. Validation logs, initial failures and resume details are in
docs/validation/part_c. No threshold, method or seed was selected after
viewing the new research outcomes. Numerical implementation corrections
are documented in the execution notes and commit history.

C7 remains blocked: no multi-week raw AIS archive was acquired or
checksummed. See data_access.md and the recorded access recheck. This
item is not represented as complete. Claude review also remains pending
until an authenticated session is available.
