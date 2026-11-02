# Development history

This folder preserves earlier reviews, raw validation records and the detailed
development changelog. Start with the [current findings](../research_results.md),
[current validation](../validation.md) or [concise changelog](../../CHANGELOG.md).

| Record | Scope |
|---|---|
| [Detailed changelog](CHANGELOG_detail.md) | Original item-by-item development record |
| [Revision notes](review_notes.md) | Corrections from the initial Python rebuild |
| [Part A](part_a_review.md), [Part B](part_b_review.md), [Part C](part_c_review.md) | Earlier audit and extension checkpoints |
| [Review request](claude_review_request.md) | Questions used for the completed external audit |
| [External audit](validation/claude/audit_2c5fe28.txt) | Claude's review of snapshot `2c5fe28`; not an endorsement of later commits |
| [Audit follow-up checks](validation/audit_followup/validation.json) | Full regeneration and local checks after that review |
| [Original validation](validation/revision_2.1.md) | Historical 118-test, nine-result checkpoint |
| [PR draft](pull_request.md) | Historical description, superseded by the live PR |

`part_b_baseline.json` and `part_c_baseline.json` remain machine inputs for
the baseline-comparison and reproduction commands. Their values are unchanged.

Review documents and raw logs were moved without editing their contents. Paths inside old records
refer to their original locations: `docs/validation/` is now
`docs/history/validation/`, and the earlier review documents now live here.
The archived revision-validation page was separated from its current pointer.
Absolute environment paths and earlier failures in logs are historical evidence.

The checksummed Git bundles remain in `archive/`: baseline comparisons import
them when the original scientific commits are absent from a snapshot clone.
Moving this index does not remove or rewrite the underlying history.
