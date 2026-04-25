"""
Food search tests covering query-length behaviour, BLS code lookup, and relevance ranking.
"""

import pytest
from rest_framework import status
from meals.models import Food

# ---------------------------------------------------------------------------
# Helpers — create isolated Food objects so tests don't depend on fixtures
# ---------------------------------------------------------------------------


def _food(bls, name, kcal):
    return Food.objects.create(
        bls_code=bls,
        name=name,
        energy_in_kj_per_100g=kcal * 4.184,
        energy_in_kcal_per_100g=kcal,
    )


@pytest.mark.django_db
class TestFoodSearchQueryLength:
    """Short or empty queries have well-defined behaviour."""

    def test_empty_search_returns_all_foods(self, authenticated_client):
        """No search parameter returns all foods (paginated)."""
        response = authenticated_client.get("/api/foods/")
        assert response.status_code == status.HTTP_200_OK
        # Without a search query the endpoint returns paginated results
        results = response.data.get("results", response.data)
        assert len(results) > 0

    def test_single_char_query_returns_empty(self, authenticated_client):
        """A 1-character query is below the 2-char threshold → empty result."""
        response = authenticated_client.get("/api/foods/?search=a")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []

    def test_two_char_query_is_accepted(self, authenticated_client):
        """Exactly 2 characters is above the threshold and triggers a real search."""
        _food("TC1", "Apple juice", 46)
        response = authenticated_client.get("/api/foods/?search=Ap")
        assert response.status_code == status.HTTP_200_OK
        # Should return at least the food we just created
        assert any("Apple" in item["name"] for item in response.data["results"])


@pytest.mark.django_db
class TestFoodSearchBLSCode:
    """BLS code is searched alongside food name."""

    def test_search_by_bls_code(self, authenticated_client):
        _food("BLS_UNIQUE_XYZ", "Generic grain", 350)
        response = authenticated_client.get("/api/foods/?search=BLS_UNIQUE_XYZ")
        assert response.status_code == status.HTTP_200_OK
        assert any(
            item["bls_code"] == "BLS_UNIQUE_XYZ" for item in response.data["results"]
        )

    def test_partial_bls_code_search(self, authenticated_client):
        _food("BLS_PARTIAL_999", "Mixed grain", 320)
        response = authenticated_client.get("/api/foods/?search=PARTIAL_999")
        assert response.status_code == status.HTTP_200_OK
        assert any(
            item["bls_code"] == "BLS_PARTIAL_999" for item in response.data["results"]
        )


@pytest.mark.django_db
class TestFoodSearchRelevanceRanking:
    """Exact name matches rank above partial matches."""

    def test_exact_name_match_ranks_first(self, authenticated_client):
        """An exact-match food should be the first result."""
        _food("RL1", "Milk", 61)
        _food("RL2", "Milk chocolate", 530)
        _food("RL3", "Skimmed milk powder", 362)

        response = authenticated_client.get("/api/foods/?search=Milk")
        assert response.status_code == status.HTTP_200_OK
        # The exact match "Milk" should appear before partial matches
        names = [item["name"] for item in response.data["results"]]
        milk_index = names.index("Milk")
        milk_choc_index = names.index("Milk chocolate")
        assert milk_index < milk_choc_index

    def test_startswith_ranks_above_contains(self, authenticated_client):
        """Foods whose name starts with the query rank above those that merely contain it."""
        _food("RL4", "Apple juice", 46)  # contains "Apple"
        _food("RL5", "Apple", 52)  # exact
        _food("RL6", "Pineapple", 50)  # contains embedded "apple"

        response = authenticated_client.get("/api/foods/?search=Apple")
        assert response.status_code == status.HTTP_200_OK
        names = [item["name"] for item in response.data["results"]]
        apple_idx = names.index("Apple")
        pineapple_idx = names.index("Pineapple")
        assert apple_idx < pineapple_idx
