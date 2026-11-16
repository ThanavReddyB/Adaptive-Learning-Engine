from typing import Any, Dict, List, Optional

import faiss
import numpy as np

from utils.config import VECTOR_DIM
from utils.embeddings import embed_text, embed_texts


class VectorStore:
    """
    FAISS-backed vector store.
    Supports per-topic filtering and similarity search.
    """

    def __init__(self) -> None:
        self.index: faiss.IndexFlatL2 = faiss.IndexFlatL2(VECTOR_DIM)
        self.documents: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add(self, text: str, metadata: Dict[str, Any]) -> int:
        if not text.strip():
            return -1
        embedding = embed_text(text).reshape(1, -1)
        self.index.add(embedding)
        doc_id = len(self.documents)
        self.documents.append({"id": doc_id, "text": text, "metadata": metadata})
        return doc_id

    def add_batch(
        self, texts: List[str], metadatas: List[Dict[str, Any]]
    ) -> List[int]:
        clean = [(t, m) for t, m in zip(texts, metadatas) if t.strip()]
        if not clean:
            return []

        clean_texts, clean_metas = zip(*clean)
        embeddings = embed_texts(list(clean_texts))
        self.index.add(embeddings)

        start_id = len(self.documents)
        ids: List[int] = []
        for i, (text, meta) in enumerate(zip(clean_texts, clean_metas)):
            doc_id = start_id + i
            self.documents.append({"id": doc_id, "text": text, "metadata": meta})
            ids.append(doc_id)
        return ids

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        k: int = 5,
        filter_topic: Optional[str] = None,
        filter_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if self.index.ntotal == 0 or not query.strip():
            return []

        # Over-fetch so we have room to filter
        k_raw = min(k * 5 if (filter_topic or filter_type) else k, self.index.ntotal)
        query_vec = embed_text(query).reshape(1, -1)
        distances, indices = self.index.search(query_vec, k_raw)

        results: List[Dict[str, Any]] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                break
            doc = self.documents[idx]
            meta = doc.get("metadata", {})

            if filter_topic and meta.get("topic") != filter_topic:
                continue
            if filter_type and meta.get("type") != filter_type:
                continue

            results.append({**doc, "distance": float(dist)})
            if len(results) >= k:
                break

        return results

    @property
    def total(self) -> int:
        return self.index.ntotal


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
