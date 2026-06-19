"""Per-geography config and calibration validity (pre-flight for Step 1)."""
from __future__ import annotations

import datetime as dt
import pathlib

from pydantic import BaseModel

from . import METHODOLOGY_VERSION

_VALID_VERDICTS = {"PASS", "PASS WITH CORRECTION", "PASS WITH WIDER RANGES"}


def _front_matter(path: pathlib.Path) -> dict:
    text = path.read_text()
    if not text.startswith("---"):
        return {}
    block = text.split("---", 2)[1]
    out: dict = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        val = raw.strip()
        if val.startswith("[") and val.endswith("]"):
            items = [x.strip().strip('"') for x in val[1:-1].split(",") if x.strip()]
            out[key.strip()] = items
        else:
            out[key.strip()] = val.strip('"')
    return out


class CalibrationStatus(BaseModel):
    exists: bool
    date: str | None = None
    verdict: str | None = None
    methodology_version: str | None = None
    types_covered: set[str] = set()


class GeographyConfig(BaseModel):
    slug: str
    name: str
    sub_postcodes: list[str]
    calibration: CalibrationStatus


def _latest_calibration(geo_dir: pathlib.Path) -> CalibrationStatus:
    cal_dir = geo_dir / "calibration"
    files = sorted(cal_dir.glob("*.md")) if cal_dir.is_dir() else []
    if not files:
        return CalibrationStatus(exists=False)
    fm = _front_matter(files[-1])
    return CalibrationStatus(
        exists=True,
        date=fm.get("date"),
        verdict=fm.get("verdict"),
        methodology_version=fm.get("methodology_version"),
        types_covered=set(fm.get("types_covered", [])),
    )


def load_geography(geo_dir: str | pathlib.Path) -> GeographyConfig:
    geo_dir = pathlib.Path(geo_dir)
    fm = _front_matter(geo_dir / "area_definition.md")
    return GeographyConfig(
        slug=fm["slug"], name=fm["name"],
        sub_postcodes=fm.get("sub_postcodes", []),
        calibration=_latest_calibration(geo_dir),
    )


def calibration_validity(cfg: GeographyConfig, today: str,
                         subject_type: str) -> tuple[bool, str]:
    c = cfg.calibration
    if not c.exists:
        return False, "no calibration on record for this area"
    if c.verdict not in _VALID_VERDICTS:
        return False, f"calibration verdict {c.verdict!r} does not permit verdicts"
    if c.methodology_version != METHODOLOGY_VERSION:
        return False, (f"calibration ran under methodology {c.methodology_version}, "
                       f"current is {METHODOLOGY_VERSION}")
    age = (dt.date.fromisoformat(today) - dt.date.fromisoformat(c.date)).days
    if age > 90:
        return False, f"calibration is {age} days old, older than 90 days"
    if subject_type not in c.types_covered:
        return False, f"type {subject_type} not represented in the calibration sample"
    return True, "valid"
