"""Thin wrapper over faiss.IndexFlatL2. Exact, deterministic nearest neighbours."""
from __future__ import annotations

import faiss
import numpy as np


class CompIndex:
    def __init__(self):
        self._index = None
        self._ids: list[str] = []

    def build(self, matrix: np.ndarray, ids: list[str]) -> "CompIndex":
        matrix = np.ascontiguousarray(matrix.astype(np.float32))
        self._index = faiss.IndexFlatL2(matrix.shape[1])
        self._index.add(matrix)
        self._ids = list(ids)
        return self

    def query(self, vec: np.ndarray, k: int) -> list[tuple[str, float]]:
        k = min(k, len(self._ids))
        q = np.ascontiguousarray(vec.reshape(1, -1).astype(np.float32))
        dists, idxs = self._index.search(q, k)
        return [(self._ids[i], float(d)) for d, i in zip(dists[0], idxs[0]) if i != -1]
