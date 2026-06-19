import numpy as np
from house_price_tool.vectorstore import CompIndex


def test_query_returns_nearest_first():
    mat = np.array([[0, 0], [1, 0], [5, 0]], dtype=np.float32)
    idx = CompIndex().build(mat, ["a", "b", "c"])
    hits = idx.query(np.array([0, 0], dtype=np.float32), k=2)
    assert [h[0] for h in hits] == ["a", "b"]


def test_k_capped_at_size():
    mat = np.array([[0, 0]], dtype=np.float32)
    idx = CompIndex().build(mat, ["a"])
    assert len(idx.query(np.array([0, 0], dtype=np.float32), k=20)) == 1
