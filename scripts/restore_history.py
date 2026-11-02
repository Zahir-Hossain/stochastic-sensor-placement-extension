"""Restore the checksummed scientific Git bundle from transport-sized parts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def restore_bundle() -> Path:
    folder = Path("archive")
    manifest = json.loads((folder / "history.json").read_text())
    target = folder / "research-history.bundle"
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != manifest["sha256"]:
            raise ValueError("existing history bundle checksum differs")
        return target
    temporary = target.with_suffix(".bundle.tmp")
    digest = hashlib.sha256()
    with temporary.open("wb") as output:
        for part in manifest["parts"]:
            data = (folder / part["path"]).read_bytes()
            if len(data) != part["size"] or hashlib.sha256(data).hexdigest() != part["sha256"]:
                raise ValueError(f"history part checksum differs: {part['path']}")
            output.write(data)
            digest.update(data)
    if digest.hexdigest() != manifest["sha256"]:
        raise ValueError("assembled history bundle checksum differs")
    temporary.rename(target)
    return target


if __name__ == "__main__":
    bundle = restore_bundle()
    subprocess.run(["git", "bundle", "verify", str(bundle)], check=True)
