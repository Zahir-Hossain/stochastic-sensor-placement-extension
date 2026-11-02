# Research commit history

This self-contained Git bundle, stored in checksummed parts, preserves the per-item scientific history
through `5b1d3e9b8037614c841d3aa8920276714f32100a`. SHA-256: `023fbdb7f96e1afbab39636f5f33d368ecf38cb77c8fcb80735d9c3df58c9c29`.

The connected GitHub API publishes a review snapshot with the exact local
root tree because the shell has no GitHub push credentials. The API does
not preserve arbitrary original commit timestamps, so the original local
commit identities are retained here rather than recreated. The remote
snapshot parent is the existing main branch; main is not changed.

Import the scientific history in a fresh checkout:

```sh
python scripts/restore_history.py
git bundle verify archive/research-history.bundle
git fetch archive/research-history.bundle refs/heads/research-hardening:refs/remotes/review-history/research-hardening
```

The summary comparison script imports this bundle automatically when its
recorded baseline commit is absent (for example in a shallow snapshot clone).
The final archive/documentation commit is outside the bundle to avoid a
self-referential archive. No history was rewritten.

`history.json` records every part's size and SHA-256, plus the complete
bundle digest. Parts keep each connected GitHub upload below its 16 MiB
request limit. Reassembly verifies every digest before importing history.
