# Skeptics 10x10 — Round 0

**A+ cells: 78 / 100**  (not yet all A+)

Rows = graders (skeptics), columns = inputs. A cell is A+ only when that skeptic's every check passes.

| Grader | I1 | I2 | I3 | I4 | I5 | I6 | I7 | I8 | I9 | I10 |
|---|---|---|---|---|---|---|---|---|---|---|
| **G1** Provenance Auditor | D | A+ | A+ | A+ | A+ | A+ | A+ | D | A+ | A+ |
| **G2** Calibration Statistician | F | F | F | A+ | A+ | A+ | A+ | A+ | A+ | A+ |
| **G3** Abstention Hawk | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ |
| **G4** Retrieval Skeptic | D | A+ | D | A+ | A+ | A+ | A+ | D | A+ | A+ |
| **G5** Faithfulness Inquisitor | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | D |
| **G6** Gate Lawyer | D | D | D | A+ | A+ | A+ | A+ | D | A+ | D |
| **G7** Schema/Contract Pedant | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ |
| **G8** Adversary/Red-teamer | D | D | D | A+ | A+ | A+ | A+ | D | A+ | D |
| **G9** Reproducibility Referee | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ | A+ |
| **G10** Honest-Communication Critic | F | F | F | A+ | A+ | A+ | A+ | A+ | A+ | A+ |

## Sub-A+ cells (evidence)

- **G1×I1** = D (Provenance Auditor): g1.checksum_verified
    - g1.checksum_verified: sl6-maidenhead is absent from the snapshot manifest: values rely on UNVERIFIED data
- **G10×I1** = F (Honest-Communication Critic): g10.withholding_communicated, g10.no_false_precision
    - g10.withholding_communicated: directional read on an unproven area with no plain withholding statement
    - g10.no_false_precision: High confidence presented as if the area's coverage were proven
- **G2×I1** = F (Calibration Statistician): g2.directional_disclosed, g2.no_unqualified_high_confidence
    - g2.directional_disclosed: directional verdict on a QUARANTINE area, presented without withholding disclosure
    - g2.no_unqualified_high_confidence: claims High confidence while the area's calibration is QUARANTINE (coverage ~ chance)
- **G4×I1** = D (Retrieval Skeptic): g4.recall_meets_bar
    - g4.recall_meets_bar: 8/10 rule-valid comps retrieved in top-20
- **G6×I1** = D (Gate Lawyer): g6.bypass_disclosed
    - g6.bypass_disclosed: gate would refuse in production, but the preview does not disclose the bypass
- **G8×I1** = D (Adversary/Red-teamer): g8.no_undisclosed_leak
    - g8.no_undisclosed_leak: result emitted for an area the gate refuses, with no withholding disclosure (leak)
- **G5×I10** = D (Faithfulness Inquisitor): g5.no_unsupported_qualitative_claim
    - g5.no_unsupported_qualitative_claim: prose claims 'methods support the stated range' but the result has no methods/range
- **G6×I10** = D (Gate Lawyer): g6.bypass_disclosed
    - g6.bypass_disclosed: gate would refuse in production, but the preview does not disclose the bypass
- **G8×I10** = D (Adversary/Red-teamer): g8.no_undisclosed_leak
    - g8.no_undisclosed_leak: result emitted for an area the gate refuses, with no withholding disclosure (leak)
- **G10×I2** = F (Honest-Communication Critic): g10.withholding_communicated, g10.no_false_precision
    - g10.withholding_communicated: directional read on an unproven area with no plain withholding statement
    - g10.no_false_precision: High confidence presented as if the area's coverage were proven
- **G2×I2** = F (Calibration Statistician): g2.directional_disclosed, g2.no_unqualified_high_confidence
    - g2.directional_disclosed: directional verdict on a QUARANTINE area, presented without withholding disclosure
    - g2.no_unqualified_high_confidence: claims High confidence while the area's calibration is QUARANTINE (coverage ~ chance)
- **G6×I2** = D (Gate Lawyer): g6.bypass_disclosed
    - g6.bypass_disclosed: gate would refuse in production, but the preview does not disclose the bypass
- **G8×I2** = D (Adversary/Red-teamer): g8.no_undisclosed_leak
    - g8.no_undisclosed_leak: result emitted for an area the gate refuses, with no withholding disclosure (leak)
- **G10×I3** = F (Honest-Communication Critic): g10.withholding_communicated, g10.no_false_precision
    - g10.withholding_communicated: directional read on an unproven area with no plain withholding statement
    - g10.no_false_precision: High confidence presented as if the area's coverage were proven
- **G2×I3** = F (Calibration Statistician): g2.directional_disclosed, g2.no_unqualified_high_confidence
    - g2.directional_disclosed: directional verdict on a QUARANTINE area, presented without withholding disclosure
    - g2.no_unqualified_high_confidence: claims High confidence while the area's calibration is QUARANTINE (coverage ~ chance)
- **G4×I3** = D (Retrieval Skeptic): g4.recall_meets_bar
    - g4.recall_meets_bar: 11/19 rule-valid comps retrieved in top-20
- **G6×I3** = D (Gate Lawyer): g6.bypass_disclosed
    - g6.bypass_disclosed: gate would refuse in production, but the preview does not disclose the bypass
- **G8×I3** = D (Adversary/Red-teamer): g8.no_undisclosed_leak
    - g8.no_undisclosed_leak: result emitted for an area the gate refuses, with no withholding disclosure (leak)
- **G1×I8** = D (Provenance Auditor): g1.checksum_verified
    - g1.checksum_verified: sl6-maidenhead is absent from the snapshot manifest: values rely on UNVERIFIED data
- **G4×I8** = D (Retrieval Skeptic): g4.recall_meets_bar
    - g4.recall_meets_bar: 10/16 rule-valid comps retrieved in top-20
- **G6×I8** = D (Gate Lawyer): g6.bypass_disclosed
    - g6.bypass_disclosed: gate would refuse in production, but the preview does not disclose the bypass
- **G8×I8** = D (Adversary/Red-teamer): g8.no_undisclosed_leak
    - g8.no_undisclosed_leak: result emitted for an area the gate refuses, with no withholding disclosure (leak)
