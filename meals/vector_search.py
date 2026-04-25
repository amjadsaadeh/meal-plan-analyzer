"""
Semantic food search using SBERT embeddings and ChromaDB.

Singletons are lazy-loaded on first use so import cost is zero until
the first search request arrives (avoids slowing down management commands,
migrations, and test collection that do not need vector search).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    import chromadb
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

FOOD_SEARCH_VECTOR_LIMIT = 30

_COLLECTION_NAME = "foods"

# Module-level singletons – None until first call
_model: "SentenceTransformer | None" = None
_collection: "chromadb.Collection | None" = None


def _get_model() -> "SentenceTransformer":
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        model_name = getattr(
            settings, "SBERT_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2"
        )
        logger.info("Loading SBERT model: %s", model_name)
        _model = SentenceTransformer(model_name)
    return _model


def _get_collection() -> "chromadb.Collection":
    global _collection
    if _collection is None:
        import chromadb

        db_path = str(getattr(settings, "CHROMA_DB_PATH", "chroma_db"))
        client = chromadb.PersistentClient(path=db_path)
        _collection = client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def search_foods(
    query: str, limit: int = FOOD_SEARCH_VECTOR_LIMIT
) -> list[tuple[str, str | None]]:
    """Return up to *limit* ``(bls_code, matched_alias_or_None)`` tuples.

    Results are ordered by cosine similarity descending (most semantically
    similar first). A ``None`` second element means the food matched by its
    canonical name; a non-None string is the alias text that caused the match.

    Deduplication: if the same bls_code appears as both a name hit and an
    alias hit, the name match wins (matched_alias set to None).

    Returns an empty list when the ChromaDB collection has no documents,
    which signals the caller to fall back to SQL search.
    """
    collection = _get_collection()

    if collection.count() == 0:
        return []

    model = _get_model()
    embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(limit, collection.count()),
        include=["metadatas"],
    )

    seen: dict[str, str | None] = {}  # bls_code → matched_alias (None = name match)

    for meta in results.get("metadatas", [[]])[0]:
        bls_code = meta["bls_code"]
        doc_type = meta.get("type", "name")
        alias_text: str | None = meta.get("alias") or None

        if bls_code not in seen:
            seen[bls_code] = None if doc_type == "name" else alias_text
        elif doc_type == "name":
            # Upgrade an alias match to a name match for the same food
            seen[bls_code] = None

    return list(seen.items())
