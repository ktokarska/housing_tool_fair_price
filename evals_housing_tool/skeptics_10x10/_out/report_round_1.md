# Skeptics 10x10 — Round 1

**A+ cells: 94 / 100**  (not yet all A+)

Rows = graders (skeptics), columns = inputs. A cell is A+ only when that skeptic's every check passes.

| Grader | I1 | I2 | I3 | I4 | I5 | I6 | I7 | I8 | I9 | I10 |
|---|---|---|---|---|---|---|---|---|---|---|
| **G1** Provenance Auditor | D | A+ | A+ | A+ | A+ | A+ | A+ | D | A+ | A+ |
| **G2** Calibration Statistician | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ |
| **G3** Abstention Hawk | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ |
| **G4** Retrieval Skeptic | D | A+ | D | A+ | A+ | A+ | A+ | D | A+ | A+ |
| **G5** Faithfulness Inquisitor | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | D |
| **G6** Gate Lawyer | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ |
| **G7** Schema/Contract Pedant | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ |
| **G8** Adversary/Red-teamer | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ |
| **G9** Reproducibility Referee | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ |
| **G10** Honest-Communication Critic | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ |

## Sub-A+ cells (evidence)

- **G1×I1** = D (Provenance Auditor): g1.checksum_verified
    - g1.checksum_verified: sl6-maidenhead is absent from the snapshot manifest: values rely on UNVERIFIED data
- **G4×I1** = D (Retrieval Skeptic): g4.recall_meets_bar
    - g4.recall_meets_bar: 8/10 rule-valid comps retrieved in top-20
- **G5×I10** = D (Faithfulness Inquisitor): g5.no_unsupported_qualitative_claim
    - g5.no_unsupported_qualitative_claim: prose claims 'methods support the stated range' but the result has no methods/range
- **G4×I3** = D (Retrieval Skeptic): g4.recall_meets_bar
    - g4.recall_meets_bar: 11/19 rule-valid comps retrieved in top-20
- **G1×I8** = D (Provenance Auditor): g1.checksum_verified
    - g1.checksum_verified: sl6-maidenhead is absent from the snapshot manifest: values rely on UNVERIFIED data
- **G4×I8** = D (Retrieval Skeptic): g4.recall_meets_bar
    - g4.recall_meets_bar: 10/16 rule-valid comps retrieved in top-20
