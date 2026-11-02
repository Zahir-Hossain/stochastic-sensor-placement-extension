# Current validation

The presentation follow-up builds on published audit-fix commit `235bc59`.
Package source, study runners, configurations and saved results are unchanged.
The [full audit resolutions](audit_followup.md) and
[presentation changes](presentation_followup.md) describe the two stages.

| Check | Latest local result |
|---|---|
| Full pytest suite | **161 passed, 1 skipped**; includes three added transport checks |
| Octave parity | Unavailable locally; runs in the dedicated hosted CI job |
| Ruff lint, Ruff format, mypy | Pass |
| Quickstart | Pass |
| Result provenance and raw-to-summary checks | All 19 result sets verify against unchanged package source `9012cb66318e` |
| Original pre-extension summaries | All 9 CSV summaries match `3b8548d`, maximum difference zero |
| Published audit-fix summaries | All 18 CSV summaries match `235bc59`, maximum difference zero |
| Overview table, figure data and report macros | Generated from saved runs; checked by `presentation_summary.py --check` |
| Technical report | Rebuilt, 14 pages; rendered and visually inspected |

The [machine check record](history/validation/presentation_followup/validation.json)
and [complete local log](history/validation/presentation_followup/checks.log)
record the commands, environment and outcomes. Summary comparisons enforce
absolute tolerance 1e-9 and relative tolerance zero. No scientific study
needed regeneration for these presentation, navigation and test changes.

## Hosted CI and external review

[PR #1](https://github.com/Zahir-Hossain/stochastic-sensor-placement-extension/pull/1)
shows checks on the current published head. The immediately preceding head
`235bc59db19a39bd69ca9e18a1c6fbec8e4408fd` passed all eight CI jobs, including
Python 3.10-3.13, Octave parity, result provenance and smoke experiments:
[exact run record](history/validation/presentation_followup/hosted_ci_235bc59.json).
That record is evidence for that commit, not a claim about later commits.

Claude's completed external audit concerns the older snapshot `2c5fe28`.
Its [captured report](history/validation/claude/audit_2c5fe28.txt) found no
result-changing implementation defect, but identified verified logging,
default and disclosure issues addressed in the audit follow-up. It is not
an approval of this later presentation change.

## Scope and reproduction

The additional transport checks compare the bound with a separate primal LP
at the study grid size for two radii, and the concentrated-mass distance with
a separately written Kantorovich dual LP. These improve numerical coverage;
they do not establish forecast calibration or optimal outer placement.

```bash
python scripts/check.py --full
python scripts/verify_artifacts.py
python scripts/compare_summaries.py --base 3b8548d
python scripts/compare_summaries.py --base 235bc59
python scripts/presentation_summary.py --check
```

Earlier counts and raw records are indexed in [history](history/README.md).
Green checks establish software consistency, not operational performance,
calibrated uncertainty or publication-level novelty. C7 remains blocked by
raw archive access; no multi-week outcome is claimed.
