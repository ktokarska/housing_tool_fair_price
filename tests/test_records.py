from house_price_tool.records import MetricRecord, SourceRef


def test_metric_record_to_dict_has_canonical_shape():
    rec = MetricRecord(metric="recall@K", gate_id="H3", score=1.0,
                       threshold=0.95, success=True, reason="18/18 retrieved")
    assert rec.to_dict() == {
        "metric": "recall@K", "gate_id": "H3", "score": 1.0,
        "threshold": 0.95, "success": True, "reason": "18/18 retrieved",
    }


def test_source_ref_rejects_unknown_dataset():
    import pytest
    with pytest.raises(ValueError):
        SourceRef(dataset="zoopla", row_id="x", url="http://e")
