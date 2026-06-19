import pathlib

import pytest

from house_price_tool.snapshot import (
    load_snapshot, sha256_of, Snapshot, SnapshotIntegrityError,
)

FIX = pathlib.Path(__file__).parent / "fixtures" / "snap"


def test_loads_verified_snapshot():
    snap = load_snapshot(FIX)
    assert isinstance(snap, Snapshot)
    assert snap.date == "2026-06-19"
    assert "sl6-maidenhead" in snap.geographies
    assert len(snap.sold("sl6-maidenhead")) == 2
    assert len(snap.epc("sl6-maidenhead")) == 2


def test_checksum_mismatch_raises(tmp_path):
    import shutil
    dst = tmp_path / "snap"
    shutil.copytree(FIX, dst)
    sold = dst / "sl6-maidenhead" / "sold.csv"
    sold.write_text(sold.read_text() + "\n# tampered\n")
    with pytest.raises(SnapshotIntegrityError):
        load_snapshot(dst)
