"""Build the 10x10 matrix: every grader against every captured run output.

    python -m evals_housing_tool.skeptics_10x10.grade_10x10 --round 0 [out_dir]

Writes <out_dir>/grades/round_<N>.json and <out_dir>/report_round_<N>.md.
"""
from __future__ import annotations

import argparse
import json
import pathlib

from .graders import GRADERS
from .inputs import INPUTS, execute
from .run_10x10 import run_all
from .snapshot_manifest import verified_geographies

ORDER = [f"I{i}" for i in range(1, 11)]


def _spec(iid):
    return next(s for s in INPUTS if s.id == iid)


def build_matrix(round_n: int, out_dir: str | pathlib.Path) -> dict:
    out = pathlib.Path(out_dir)
    runs = run_all(out)  # captures fresh real outputs
    verified = verified_geographies()

    cells = []
    for iid in ORDER:
        output = runs[iid]["output"]
        ctx = {"verified_geos": verified, "input_id": iid,
               "reexecute": (lambda s=_spec(iid): execute(s))}
        for g in GRADERS:
            cell = g.fn(output, ctx)
            cells.append({
                "grader": g.id, "persona": g.persona, "input": iid,
                "grade": cell.grade, "failed_checks": cell.failed_checks,
                "evidence": cell.evidence,
            })

    a_plus = sum(1 for c in cells if c["grade"] == "A+")
    matrix = {"round": round_n, "total": len(cells), "a_plus": a_plus,
              "all_a_plus": a_plus == len(cells), "cells": cells}

    grades_dir = out / "grades"
    grades_dir.mkdir(parents=True, exist_ok=True)
    (grades_dir / f"round_{round_n}.json").write_text(
        json.dumps(matrix, indent=2, sort_keys=True) + "\n")
    (out / f"report_round_{round_n}.md").write_text(_render(matrix))
    return matrix


def _render(matrix: dict) -> str:
    by = {(c["grader"], c["input"]): c for c in matrix["cells"]}
    gids = [f"G{i}" for i in range(1, 11)]
    lines = [f"# Skeptics 10x10 — Round {matrix['round']}", "",
             f"**A+ cells: {matrix['a_plus']} / {matrix['total']}**  "
             f"({'ALL A+' if matrix['all_a_plus'] else 'not yet all A+'})", "",
             "Rows = graders (skeptics), columns = inputs. A cell is A+ only when that "
             "skeptic's every check passes.", "",
             "| Grader | " + " | ".join(ORDER) + " |",
             "|" + "---|" * (len(ORDER) + 1)]
    for gid in gids:
        persona = next(g.persona for g in GRADERS if g.id == gid)
        row = [f"**{gid}** {persona}"]
        for iid in ORDER:
            row.append(by[(gid, iid)]["grade"])
        lines.append("| " + " | ".join(row) + " |")

    lines += ["", "## Sub-A+ cells (evidence)", ""]
    sub = [c for c in matrix["cells"] if c["grade"] != "A+"]
    if not sub:
        lines.append("None — every skeptic gave every input an A+.")
    for c in sorted(sub, key=lambda c: (c["input"], c["grader"])):
        lines.append(f"- **{c['grader']}×{c['input']}** = {c['grade']} "
                     f"({c['persona']}): {', '.join(c['failed_checks'])}")
        for ev in c["evidence"]:
            if ev.startswith("XX "):
                lines.append(f"    - {ev[3:]}")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=0)
    ap.add_argument("out_dir", nargs="?", default="evals_housing_tool/skeptics_10x10/_out")
    args = ap.parse_args()
    m = build_matrix(args.round, args.out_dir)
    print(f"Round {args.round}: {m['a_plus']}/{m['total']} A+  "
          f"({'ALL A+' if m['all_a_plus'] else 'sub-A+ remain'})")


if __name__ == "__main__":
    main()
