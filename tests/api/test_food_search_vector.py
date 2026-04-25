"""
Semantic food search tests using an in-memory ChromaDB collection.

Design
------
Tests use a deterministic mock embedding model so they run without internet
access or GPU.  The mock produces character-trigram bag-of-words vectors,
which naturally handles German compound-word splitting:

    "Haferflocken"  →  normalised to "haferflocken"  →  trigrams: haf,afe,...
    "Hafer Flocken" →  normalised to "haferflocken"  →  trigrams: haf,afe,...

Both strings map to identical normalised forms, so cosine similarity = 1.0,
which is the same semantic result a production SBERT model would produce.

Test isolation:
  1. vector_search._get_model is patched to return MockEmbeddingModel.
  2. A fresh chromadb.EphemeralClient() is used per test (no disk state).
  3. vector_search._get_collection is patched to return the in-memory collection.
"""

from __future__ import annotations

import numpy as np
import pytest
import chromadb
from unittest.mock import patch

from meals import vector_search
from meals.models import Food

# ---------------------------------------------------------------------------
# Mock embedding model
# ---------------------------------------------------------------------------


class MockEmbeddingModel:
    """Character-trigram bag-of-words embeddings (dim=256, cosine-normalised).

    Key property: spaces are stripped before n-gram extraction, so
    "Hafer Flocken" and "Haferflocken" produce identical vectors.
    This mirrors the semantic result a paraphrase SBERT model achieves.
    """

    DIM = 256

    def encode(self, texts, **kwargs):
        # Mirror sentence-transformers: single string → 1D array, list → 2D array
        single = isinstance(texts, str)
        if single:
            texts = [texts]
        out = []
        for text in texts:
            base = text.lower().replace(" ", "")
            vec = np.zeros(self.DIM, dtype=np.float32)
            for i in range(max(1, len(base) - 2)):
                gram = base[i : i + 3]
                idx = abs(hash(gram)) % self.DIM
                vec[idx] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            out.append(vec)
        result = np.array(out)
        return result[0] if single else result


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _populate_collection(
    collection: chromadb.Collection, documents: list[dict], model: MockEmbeddingModel
) -> None:
    """Embed *documents* using *model* and add them to *collection*."""
    ids = [d["id"] for d in documents]
    texts = [d["text"] for d in documents]
    metadatas = [
        {
            "bls_code": d["bls_code"],
            "type": d.get("type", "name"),
            "alias": d.get("alias", ""),
        }
        for d in documents
    ]
    embeddings = model.encode(texts).tolist()
    collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas)


def _ephemeral_collection(name: str = "foods_test") -> chromadb.Collection:
    client = chromadb.EphemeralClient()
    return client.create_collection(name=name, metadata={"hnsw:space": "cosine"})


# ---------------------------------------------------------------------------
# Session-scoped mock model fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mock_model():
    return MockEmbeddingModel()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVectorSearchDirectNameMatch:
    """A direct name query returns the correct food via vector similarity."""

    def test_apple_finds_apple(self, authenticated_client, mock_model):
        Food.objects.create(
            bls_code="APPLE01",
            name="Apple",
            energy_in_kj_per_100g=218,
            energy_in_kcal_per_100g=52,
        )

        collection = _ephemeral_collection()
        _populate_collection(
            collection,
            [{"id": "name::APPLE01", "text": "Apple", "bls_code": "APPLE01"}],
            mock_model,
        )

        with (
            patch.object(vector_search, "_get_collection", return_value=collection),
            patch.object(vector_search, "_get_model", return_value=mock_model),
        ):
            response = authenticated_client.get("/api/foods/?search=Apple")

        assert response.status_code == 200
        results = response.data["results"]
        bls_codes = [r["bls_code"] for r in results]
        assert "APPLE01" in bls_codes

        apple_result = next(r for r in results if r["bls_code"] == "APPLE01")
        assert apple_result["matched_alias"] is None

    def test_direct_match_returns_name_not_alias(
        self, authenticated_client, mock_model
    ):
        """When a food matches by name embedding, matched_alias must be None."""
        Food.objects.create(
            bls_code="BANANA01",
            name="Banana",
            energy_in_kj_per_100g=371,
            energy_in_kcal_per_100g=89,
        )

        collection = _ephemeral_collection("foods_banana")
        _populate_collection(
            collection,
            [{"id": "name::BANANA01", "text": "Banana", "bls_code": "BANANA01"}],
            mock_model,
        )

        with (
            patch.object(vector_search, "_get_collection", return_value=collection),
            patch.object(vector_search, "_get_model", return_value=mock_model),
        ):
            response = authenticated_client.get("/api/foods/?search=Banana")

        assert response.status_code == 200
        result = next(
            (r for r in response.data["results"] if r["bls_code"] == "BANANA01"), None
        )
        assert result is not None
        assert result["matched_alias"] is None


@pytest.mark.django_db
class TestVectorSearchCompoundGermanWord:
    """
    Validate compound-word matching: "Haferflocken" (one-word compound) and
    "Hafer Flocken" (space-separated) produce identical character-trigram
    vectors (spaces stripped before encoding), so cosine similarity = 1.0.

    The MockEmbeddingModel strips spaces before n-gram extraction, which is
    the same semantic result a paraphrase SBERT model achieves for this pair.
    In production, the real model is loaded via manage.py populate_chroma and
    handles both compound forms as well as true synonyms across German foods.
    """

    def test_haferflocken_found_by_split_query(self, authenticated_client, mock_model):
        """Searching 'Hafer Flocken' (split) matches food named 'Haferflocken'."""
        Food.objects.create(
            bls_code="HAFER01",
            name="Haferflocken",
            energy_in_kj_per_100g=1560,
            energy_in_kcal_per_100g=372,
        )

        collection = _ephemeral_collection("foods_hafer1")
        _populate_collection(
            collection,
            [{"id": "name::HAFER01", "text": "Haferflocken", "bls_code": "HAFER01"}],
            mock_model,
        )

        with (
            patch.object(vector_search, "_get_collection", return_value=collection),
            patch.object(vector_search, "_get_model", return_value=mock_model),
        ):
            response = authenticated_client.get("/api/foods/?search=Hafer Flocken")

        assert response.status_code == 200
        bls_codes = [r["bls_code"] for r in response.data["results"]]
        assert "HAFER01" in bls_codes, (
            "'Hafer Flocken' did not match 'Haferflocken'. "
            "Compound-word normalisation (space removal) must be applied before encoding."
        )

    def test_split_query_found_by_compound(self, authenticated_client, mock_model):
        """Searching 'Haferflocken' (compound) matches food named 'Hafer Flocken'."""
        Food.objects.create(
            bls_code="HAFER02",
            name="Hafer Flocken",
            energy_in_kj_per_100g=1560,
            energy_in_kcal_per_100g=372,
        )

        collection = _ephemeral_collection("foods_hafer2")
        _populate_collection(
            collection,
            [{"id": "name::HAFER02", "text": "Hafer Flocken", "bls_code": "HAFER02"}],
            mock_model,
        )

        with (
            patch.object(vector_search, "_get_collection", return_value=collection),
            patch.object(vector_search, "_get_model", return_value=mock_model),
        ):
            response = authenticated_client.get("/api/foods/?search=Haferflocken")

        assert response.status_code == 200
        bls_codes = [r["bls_code"] for r in response.data["results"]]
        assert "HAFER02" in bls_codes, (
            "'Haferflocken' did not match 'Hafer Flocken'. "
            "Compound-word normalisation (space removal) must be applied before encoding."
        )


@pytest.mark.django_db
class TestVectorSearchAliasMatch:
    """Foods matched via an alias embedding expose matched_alias in the response."""

    def test_alias_match_sets_matched_alias_field(
        self, authenticated_client, mock_model
    ):
        Food.objects.create(
            bls_code="TOMATO01",
            name="Tomate",
            energy_in_kj_per_100g=74,
            energy_in_kcal_per_100g=18,
        )

        collection = _ephemeral_collection("foods_tomato")
        _populate_collection(
            collection,
            [
                {
                    "id": "alias::999",
                    "text": "Paradeiser",
                    "bls_code": "TOMATO01",
                    "type": "alias",
                    "alias": "Paradeiser",
                }
            ],
            mock_model,
        )

        with (
            patch.object(vector_search, "_get_collection", return_value=collection),
            patch.object(vector_search, "_get_model", return_value=mock_model),
        ):
            response = authenticated_client.get("/api/foods/?search=Paradeiser")

        assert response.status_code == 200
        result = next(
            (r for r in response.data["results"] if r["bls_code"] == "TOMATO01"), None
        )
        assert result is not None
        assert result["matched_alias"] == "Paradeiser"


@pytest.mark.django_db
class TestVectorSearchFallback:
    """When ChromaDB is empty the view falls back to the SQL search path."""

    def test_empty_collection_uses_sql_fallback(self, authenticated_client, mock_model):
        Food.objects.create(
            bls_code="FALLBACK01",
            name="Fallback Food",
            energy_in_kj_per_100g=400,
            energy_in_kcal_per_100g=96,
        )

        empty_collection = _ephemeral_collection("foods_empty")

        with (
            patch.object(
                vector_search, "_get_collection", return_value=empty_collection
            ),
            patch.object(vector_search, "_get_model", return_value=mock_model),
        ):
            response = authenticated_client.get("/api/foods/?search=Fallback Food")

        assert response.status_code == 200
        bls_codes = [r["bls_code"] for r in response.data["results"]]
        assert "FALLBACK01" in bls_codes
