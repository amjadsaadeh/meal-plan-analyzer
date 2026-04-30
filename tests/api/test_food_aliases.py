import pytest
from rest_framework import status
from meals.models import Food, FoodAlias


def _make_food(suffix="01", **kwargs):
    defaults = dict(
        bls_code=f"ALIAS{suffix}",
        name=f"Alias Test Food {suffix}",
        energy_in_kj_per_100g=100.0,
        energy_in_kcal_per_100g=24.0,
    )
    defaults.update(kwargs)
    return Food.objects.create(**defaults)


@pytest.mark.django_db
class TestFoodAliasListAndFilter:
    def test_list_unauthenticated(self, api_client):
        response = api_client.get("/api/food-aliases/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_authenticated_empty(self, authenticated_client):
        response = authenticated_client.get("/api/food-aliases/")
        assert response.status_code == status.HTTP_200_OK

    def test_list_returns_aliases(self, authenticated_client):
        food = _make_food("02")
        FoodAlias.objects.create(food=food, alias="Beta")
        FoodAlias.objects.create(food=food, alias="Alpha")
        response = authenticated_client.get("/api/food-aliases/")
        assert response.status_code == status.HTTP_200_OK
        aliases_in_response = [
            a["alias"]
            for a in (response.data.get("results") or response.data)
            if a["food"] == food.id
        ]
        assert set(aliases_in_response) == {"Alpha", "Beta"}

    def test_filter_by_food(self, authenticated_client):
        food_a = _make_food("03")
        food_b = _make_food("04")
        FoodAlias.objects.create(food=food_a, alias="OnlyA")
        FoodAlias.objects.create(food=food_b, alias="OnlyB")

        response = authenticated_client.get(f"/api/food-aliases/?food={food_a.id}")
        assert response.status_code == status.HTTP_200_OK
        aliases = response.data.get("results") or response.data
        assert len(aliases) == 1
        assert aliases[0]["alias"] == "OnlyA"
        assert aliases[0]["food"] == food_a.id

    def test_filter_by_food_returns_sorted(self, authenticated_client):
        food = _make_food("05")
        FoodAlias.objects.create(food=food, alias="Zebra")
        FoodAlias.objects.create(food=food, alias="Apple")
        FoodAlias.objects.create(food=food, alias="Mango")

        response = authenticated_client.get(f"/api/food-aliases/?food={food.id}")
        assert response.status_code == status.HTTP_200_OK
        aliases = response.data.get("results") or response.data
        assert [a["alias"] for a in aliases] == ["Apple", "Mango", "Zebra"]


@pytest.mark.django_db
class TestFoodAliasCreate:
    def test_create_unauthenticated(self, api_client):
        food = _make_food("10")
        response = api_client.post(
            "/api/food-aliases/",
            {"food": food.id, "alias": "NewAlias"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_success(self, authenticated_client):
        food = _make_food("11")
        response = authenticated_client.post(
            "/api/food-aliases/",
            {"food": food.id, "alias": "MyAlias"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["alias"] == "MyAlias"
        assert response.data["food"] == food.id
        assert FoodAlias.objects.filter(food=food, alias="MyAlias").exists()

    def test_create_duplicate_returns_existing(self, authenticated_client):
        food = _make_food("12")
        existing = FoodAlias.objects.create(food=food, alias="Duplicate")

        response = authenticated_client.post(
            "/api/food-aliases/",
            {"food": food.id, "alias": "Duplicate"},
            format="json",
        )
        # Returns 200 (or 201) — either way the alias still exists exactly once
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)
        assert response.data["id"] == existing.id
        assert FoodAlias.objects.filter(food=food, alias="Duplicate").count() == 1

    def test_create_missing_alias_field(self, authenticated_client):
        food = _make_food("13")
        response = authenticated_client.post(
            "/api/food-aliases/",
            {"food": food.id},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_empty_alias_field(self, authenticated_client):
        food = _make_food("14")
        response = authenticated_client.post(
            "/api/food-aliases/",
            {"food": food.id, "alias": "   "},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_missing_food_field(self, authenticated_client):
        response = authenticated_client.post(
            "/api/food-aliases/",
            {"alias": "NoFood"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_strips_whitespace(self, authenticated_client):
        food = _make_food("15")
        response = authenticated_client.post(
            "/api/food-aliases/",
            {"food": food.id, "alias": "  Trimmed  "},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["alias"] == "Trimmed"
        assert FoodAlias.objects.filter(food=food, alias="Trimmed").exists()


@pytest.mark.django_db
class TestFoodAliasDelete:
    def test_delete_unauthenticated(self, api_client):
        food = _make_food("20")
        alias = FoodAlias.objects.create(food=food, alias="ToDelete")
        response = api_client.delete(f"/api/food-aliases/{alias.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_success(self, authenticated_client):
        food = _make_food("21")
        alias = FoodAlias.objects.create(food=food, alias="Goodbye")
        response = authenticated_client.delete(f"/api/food-aliases/{alias.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not FoodAlias.objects.filter(id=alias.id).exists()

    def test_delete_nonexistent(self, authenticated_client):
        response = authenticated_client.delete("/api/food-aliases/99999999/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestFoodAliasMethodRestrictions:
    def test_put_not_allowed(self, authenticated_client):
        food = _make_food("30")
        alias = FoodAlias.objects.create(food=food, alias="ReadOnly")
        response = authenticated_client.put(
            f"/api/food-aliases/{alias.id}/",
            {"food": food.id, "alias": "Changed"},
            format="json",
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_patch_not_allowed(self, authenticated_client):
        food = _make_food("31")
        alias = FoodAlias.objects.create(food=food, alias="ReadOnly2")
        response = authenticated_client.patch(
            f"/api/food-aliases/{alias.id}/",
            {"alias": "Changed"},
            format="json",
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestFoodAliasDeduplication:
    def test_case_insensitive_duplicate_returns_existing(self, authenticated_client):
        food = _make_food("40")
        existing = FoodAlias.objects.create(food=food, alias="Apple")

        response = authenticated_client.post(
            "/api/food-aliases/",
            {"food": food.id, "alias": "apple"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == existing.id
        assert FoodAlias.objects.filter(food=food).count() == 1

    def test_case_insensitive_duplicate_uppercase_returns_existing(
        self, authenticated_client
    ):
        food = _make_food("41")
        existing = FoodAlias.objects.create(food=food, alias="mango juice")

        response = authenticated_client.post(
            "/api/food-aliases/",
            {"food": food.id, "alias": "Mango Juice"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == existing.id
        assert FoodAlias.objects.filter(food=food).count() == 1

    def test_alias_matching_food_name_is_rejected(self, authenticated_client):
        food = _make_food("42")
        response = authenticated_client.post(
            "/api/food-aliases/",
            {"food": food.id, "alias": "Alias Test Food 42"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "alias" in response.data
        assert not FoodAlias.objects.filter(food=food).exists()

    def test_alias_matching_food_name_case_insensitive_is_rejected(
        self, authenticated_client
    ):
        food = _make_food("43")
        response = authenticated_client.post(
            "/api/food-aliases/",
            {"food": food.id, "alias": "alias test food 43"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "alias" in response.data
        assert not FoodAlias.objects.filter(food=food).exists()

    def test_whitespace_normalized_before_dedup(self, authenticated_client):
        food = _make_food("44")
        existing = FoodAlias.objects.create(food=food, alias="Fresh Juice")

        response = authenticated_client.post(
            "/api/food-aliases/",
            {"food": food.id, "alias": "Fresh  Juice"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == existing.id
        assert FoodAlias.objects.filter(food=food).count() == 1

    def test_distinct_aliases_different_foods_are_allowed(self, authenticated_client):
        food_a = _make_food("45")
        food_b = _make_food("46")
        FoodAlias.objects.create(food=food_a, alias="SharedName")

        response = authenticated_client.post(
            "/api/food-aliases/",
            {"food": food_b.id, "alias": "sharedname"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert FoodAlias.objects.filter(food=food_b, alias="sharedname").exists()
