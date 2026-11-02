"""Download the public AIS sample used by the case study.

Source: Danish Maritime Authority AIS data (5 July 2017, near Gothenburg),
as redistributed in the MovingPandas examples repository
(https://github.com/movingpandas/movingpandas-examples, data/ais.gpkg).
The file is not committed to this repository; this script fetches it and
checks its SHA-256.

Usage: python scripts/fetch_ais_sample.py [--out data/raw/ais.gpkg]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/anitagraser/movingpandas-examples/main/data/ais.gpkg"
SHA256 = "038c98af738e29cdac5d91a1829eb88a4b7cf94fedbf6f6cf8e04982bd65e4e3"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw/ais.gpkg")
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists():
        print(f"downloading {URL}")
        urllib.request.urlretrieve(URL, out)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    if digest != SHA256:
        print(f"checksum mismatch: {digest}", file=sys.stderr)
        return 1
    print(f"ok: {out} ({out.stat().st_size / 1e6:.1f} MB, sha256 verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
