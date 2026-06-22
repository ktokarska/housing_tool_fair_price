"""Which geographies the pinned snapshot actually checksum-verifies (G1's source of truth)."""
from __future__ import annotations

import json

from .discover import snapshot_paths


def verified_geographies() -> set[str]:
    root = snapshot_paths()["snapshot_root"]
    manifest = json.loads((root / "manifest.json").read_text())
    return set(manifest.get("geographies", {}).keys())
