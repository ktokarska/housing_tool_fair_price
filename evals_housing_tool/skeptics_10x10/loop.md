# The integrity loop

Goal: every one of the 10 skeptics gives every one of the 10 inputs an A+ — reached only by honest
fixes (correct behaviour, honest disclosure, real retrieval/provenance improvements), never by
moving a calibration threshold the methodology forbids moving.

## Round 0 — baseline: 78 / 100 A+

22 sub-A+ cells, in five honest defect classes:

| Class | Cells | Root cause |
|---|---|---|
| Undisclosed engine-preview | G6,G8 × {I1,I2,I3,I8,I10} = 10 | a skip_gate preview on a refusing-gate area produced a result with no "withheld in production" disclosure |
| Overconfidence on a quarantined area | G2,G10 × {I1,I2,I3} = 6 | directional verdict + unqualified "High" confidence where the area's calibration is QUARANTINE |
| recall@K below bar | G4 × {I1,I3,I8} = 3 | the retriever's top-20 misses rule-valid comps (e.g. I3: 11/19) |
| Unverified data | G1 × {I1,I8} = 2 | sl6-maidenhead is absent from the snapshot manifest, so its data is not checksum-verified |
| Unsupported prose | G5 × {I10} = 1 | the offline placeholder claims "methods support the stated range" for a 0-method result |

No cell requires gaming: each class has an honest fix. Planned rounds:

- **Round 1** — disclose engine-preview disposition in the tool (clears the first two classes, 16 cells).
- **Round 2** — pin sl6 in the manifest; make the offline placeholder honest (clears 3 cells).
- **Round 3** — fix retrieval recall so the rule-valid comps are actually retrieved (clears 3 cells).
