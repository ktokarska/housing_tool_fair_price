"""Pinned snapshot loading with checksum verification. No network here."""
from __future__ import annotations

import hashlib
import json
import pathlib

import pandas as pd


class SnapshotIntegrityError(Exception):
    """Raised when a snapshot file is missing or its checksum does not match."""


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    h.update(pathlib.Path(path).read_bytes())
    return h.hexdigest()


class Snapshot:
    def __init__(self, date: str, root: pathlib.Path, manifest: dict):
        self.date = date
        self._root = root
        self._manifest = manifest
        self.geographies = list(manifest["geographies"].keys())

    def _read(self, geo: str, fname: str) -> pd.DataFrame:
        return pd.read_csv(self._root / geo / fname, dtype={"postcode": str})

    def sold(self, geo: str) -> pd.DataFrame:
        return self._read(geo, "sold.csv")

    def epc(self, geo: str) -> pd.DataFrame:
        return self._read(geo, "epc.csv")


def load_snapshot(snapshot_dir: str | pathlib.Path) -> Snapshot:
    root = pathlib.Path(snapshot_dir)
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        raise SnapshotIntegrityError(f"missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    for geo, spec in manifest["geographies"].items():
        for fname, meta in spec["files"].items():
            fpath = root / geo / fname
            if not fpath.exists():
                raise SnapshotIntegrityError(f"missing file: {fpath}")
            actual = sha256_of(fpath)
            if actual != meta["sha256"]:
                raise SnapshotIntegrityError(
                    f"checksum mismatch for {fpath}: "
                    f"manifest {meta['sha256']}, actual {actual}"
                )
    return Snapshot(manifest["snapshot_date"], root, manifest)
