"""Step 3: vector retrieval proposes, the rule gate disposes. Emits recall@K (H3)."""
from __future__ import annotations

from .embedding import FeatureEncoder
from .models import PropertyRecord
from .records import MetricRecord
from .rulegate import rule_valid, rule_valid_set
from .vectorstore import CompIndex

RECALL_K = 20
RECALL_THRESHOLD = 0.95


def _sold_id(rec: PropertyRecord) -> str:
    for s in rec.sources:
        if s.dataset == "sold":
            return s.row_id
    return ""


def retrieve_comps(subject: PropertyRecord, candidates: list[PropertyRecord],
                   today: str, k: int = RECALL_K,
                   threshold: float = RECALL_THRESHOLD):
    pool = [c for c in candidates if c is not subject]
    if not pool:
        rec = MetricRecord(metric="recall@K", gate_id="H3", score=1.0,
                           threshold=threshold, success=True,
                           reason="no candidate pool (0 rule-valid comps)")
        return [], rec
    enc = FeatureEncoder().fit(pool)
    matrix, ids = enc.transform_many(pool)
    index = CompIndex().build(matrix, ids)
    hits = index.query(enc.transform(subject), k=k)
    by_id = {_sold_id(c): c for c in pool}
    retrieved = [by_id[i] for i, _ in hits if i in by_id]

    valid_ids = rule_valid_set(subject, pool, today)
    retrieved_valid = {i for i, _ in hits} & valid_ids
    score = 1.0 if not valid_ids else len(retrieved_valid) / len(valid_ids)

    comps = [c for c in retrieved if rule_valid(subject, c, today)]
    rec = MetricRecord(
        metric="recall@K", gate_id="H3", score=round(score, 4),
        threshold=threshold, success=score >= threshold,
        reason=f"{len(retrieved_valid)}/{len(valid_ids)} rule-valid comps "
               f"retrieved in top-{k}",
    )
    return comps, rec
