"""Parse a geography's market_baseline.md into typed lookups."""
from __future__ import annotations

import pathlib
import re

from pydantic import BaseModel

_TYPE_COL = {"Detached": "D", "Semi-Det": "S", "Terraced": "T", "Flat": "F"}


class MarketBaseline(BaseModel):
    yoy: dict[str, float]
    psqft: dict[tuple[str, str], float]
    median_sqft: dict[tuple[str, str], float | None]


def _rows(text: str, header_contains: str) -> list[list[str]]:
    """Return the data rows of the first markdown table whose header matches."""
    out, in_table, seen_header = [], False, False
    for line in text.splitlines():
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not seen_header and header_contains in line:
                seen_header, in_table = True, True
                continue
            if in_table:
                if set("".join(cells)) <= set("-: "):  # separator row
                    continue
                out.append(cells)
        elif in_table and seen_header:
            break
    return out


def _num(s: str) -> float:
    return float(re.sub(r"[^0-9.\-]", "", s))


def load_baseline(path) -> MarketBaseline:
    text = pathlib.Path(path).read_text()
    yoy = {}
    for cells in _rows(text, "YoY %"):
        yoy[cells[0]] = _num(cells[1])
    psqft, median_sqft = {}, {}
    for cells in _rows(text, "Detached"):
        sub = cells[0]
        for col_name, code in _TYPE_COL.items():
            idx = ["Sub-PC", "Detached", "Semi-Det", "Terraced", "Flat"].index(col_name)
            try:
                value = _num(cells[idx])
            except ValueError:
                continue  # thin cell (e.g. "-"): no segment data, method unavailable here
            if value <= 0:
                continue
            psqft[(sub, code)] = value
            median_sqft[(sub, code)] = None  # populated only when a median-sqft table exists
    return MarketBaseline(yoy=yoy, psqft=psqft, median_sqft=median_sqft)


def psqft_for(baseline: MarketBaseline, sub_postcode: str, type_code: str):
    v = baseline.psqft.get((sub_postcode, type_code))
    if v is None:
        return None, f"no segment £/sq ft for ({sub_postcode}, {type_code})"
    return v, "type"
