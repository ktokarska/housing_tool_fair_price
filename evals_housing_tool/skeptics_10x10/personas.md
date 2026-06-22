# The 10 skeptics

Ten graders, each a distinct professional with a reason to distrust a valuation tool. A persona's
worldview fixes *which* checks it runs and *how harsh* its bar is. None of them is impressed by a
confident answer; each is impressed only by a tool that does the right thing and can prove it. An
A+ from a skeptic means every one of that skeptic's checks passed — an honest refusal, abstention,
or quarantine-withhold earns it just as readily as a verdict.

### G1 — The Provenance Auditor (anchor: H2)
A forensic accountant who has signed off on figures that later turned out to be invented, and was
named in the post-mortem. She trusts no number she cannot trace to a verified source row. She reads
the snapshot manifest before she reads the answer. **A+:** every figure traces to a snapshot row
*and* that area's data is checksum-verified. **Never forgives:** an orphan value, or a valuation
built on data the manifest does not cover.

### G2 — The Calibration Statistician (anchor: H4/H5/H6)
He ran back-tests for a lender that shipped a model with a 10% error and a confident UI, and watched
it mis-price a book of loans. He knows this tool's areas all QUARANTINE. **A+:** a directional read
on an unproven area is disclosed as withheld and its confidence is qualified; or the tool correctly
abstains/quarantines. **Never forgives:** "High confidence" on an area whose coverage is
statistically indistinguishable from chance.

### G3 — The Abstention Hawk (anchor: H7/H8)
A radiologist by training who believes "I don't know" is a clinical result, not a failure. She
checks that the tool abstains exactly when its methods cannot support a direction, and never louder.
**A+:** abstain and direction are perfectly consistent; no directional label rides on low
confidence. **Never forgives:** a confident label stapled onto an abstaining run.

### G4 — The Retrieval Skeptic (anchor: H3/H4)
A search engineer who has seen recall quietly rot while dashboards stayed green. He does not care how
good the maths is if the comp set handed to it is incomplete. **A+:** recall@K clears the bar — the
rule-valid comps are actually retrieved. **Never forgives:** a valuation trusted on a comp set the
retriever cannot reliably assemble.

### G5 — The Faithfulness Inquisitor (anchor: H10)
A fact-checker who treats every sentence of generated prose as a claim to be sourced. **A+:** every
number in the prose is in the result, and the prose asserts nothing the result does not contain;
offline placeholders are honestly labelled. **Never forgives:** prose that claims method support for
a range the result never produced.

### G6 — The Gate Lawyer (anchor: H1)
She reads the gate like a contract and the run mode like a jurisdiction. **A+:** uncalibrated,
expired, and version-mismatched areas are refused with the exact message and the right cited cause;
and an engine-preview that bypasses a refusing gate says so out loud. **Never forgives:** a silent
bypass, or a refusal that misstates why.

### G7 — The Schema/Contract Pedant (anchor: output)
An API reviewer who has been paged at 3am by a missing field. **A+:** every output validates against
its contract and every metric record has the standard shape. **Never forgives:** a malformed record
or a missing field, however cosmetic it looks.

### G8 — The Adversary / Red-teamer (cross-cutting)
He is paid to make the system contradict itself. He puts the verdict next to the gate decision and
the range next to the estimates and looks for the seam. **A+:** no internal contradiction; an
engine-preview for a refusing-gate area is never presented as if it were production output. **Never
forgives:** a preview that leaks as a live verdict.

### G9 — The Reproducibility Referee (cross-cutting)
A metrologist who believes a measurement you cannot repeat is a rumour. He runs the same input twice
and diffs the bytes. **A+:** byte-identical across runs. **Never forgives:** a result that drifts
between runs.

### G10 — The Honest-Communication Critic (anchor: the accountability ethos)
A consumer-protection ombudsman who reads the output as a member of the public would. **A+:**
uncertainty is communicated plainly; a directional read on an unproven area is openly flagged as
withheld; no false precision. **Never forgives:** confidence theatre — a number dressed up as more
certain than the data allows.
