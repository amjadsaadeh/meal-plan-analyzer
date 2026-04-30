import pytest
from rest_framework import status
from django.urls import reverse
from meals.models import (
    Food,
    FoodAlias,
    MealPlan,
    MealPlanDay,
    MealPlanFood,
    ALIAS_CACHE_KEY,
)
from django.core.cache import cache


@pytest.mark.django_db
class TestExportNameAutoAlias:
    @pytest.fixture
    def setup_data(self, client, admin_user):
        client.force_login(admin_user)
        food = Food.objects.create(
            bls_code="X999",
            name="Golden Apple",
            energy_in_kj_per_100g=200,
            energy_in_kcal_per_100g=50,
        )
        plan = MealPlan.objects.create(name="Audit Plan")
        day = MealPlanDay.objects.create(name="Day 1", meal_plan=plan)
        return client, food, day

    def test_alias_created_on_post_with_new_export_name(self, setup_data):
        client, food, day = setup_data
        url = reverse("mealplanfood-list")
        payload = {
            "meal_plan_day": day.id,
            "food": food.id,
            "amount_in_g": 100,
            "meal_type": "breakfast",
            "export_name": "Forbidden Fruit",
        }

        # Ensure cache is fresh for this test
        cache.delete(ALIAS_CACHE_KEY)

        response = client.post(url, payload)
        assert response.status_code == status.HTTP_201_CREATED

        # Assert alias exists
        assert FoodAlias.objects.filter(food=food, alias="Forbidden Fruit").exists()
        # Assert cache was cleared (calling cache.get will now return None because perform_create deleted it)
        assert cache.get(ALIAS_CACHE_KEY) is None

    def test_no_alias_created_if_name_matches_food_name(self, setup_data):
        client, food, day = setup_data
        url = reverse("mealplanfood-list")
        payload = {
            "meal_plan_day": day.id,
            "food": food.id,
            "amount_in_g": 100,
            "meal_type": "breakfast",
            "export_name": "Golden Apple",
        }

        response = client.post(url, payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert not FoodAlias.objects.filter(food=food, alias="Golden Apple").exists()

    def test_no_alias_created_if_name_matches_case_insensitive(self, setup_data):
        client, food, day = setup_data
        url = reverse("mealplanfood-list")
        payload = {
            "meal_plan_day": day.id,
            "food": food.id,
            "amount_in_g": 100,
            "meal_type": "breakfast",
            "export_name": "golden apple",
        }

        response = client.post(url, payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert not FoodAlias.objects.filter(food=food, alias="golden apple").exists()

    def test_alias_created_on_patch_update(self, setup_data):
        client, food, day = setup_data
        mpf = MealPlanFood.objects.create(
            meal_plan_day=day, food=food, amount_in_g=100, meal_type="lunch"
        )

        url = reverse("mealplanfood-detail", args=[mpf.id])
        payload = {"export_name": "Shiny Fruit"}

        response = client.patch(url, payload, content_type="application/json")
        assert response.status_code == status.HTTP_200_OK
        assert FoodAlias.objects.filter(food=food, alias="Shiny Fruit").exists()

    def test_no_alias_for_short_names(self, setup_data):
        """Names under 2 characters should not trigger alias creation to avoid spamming aliases with 'a', 'x', etc."""
        client, food, day = setup_data
        url = reverse("mealplanfood-list")
        payload = {
            "meal_plan_day": day.id,
            "food": food.id,
            "amount_in_g": 100,
            "meal_type": "breakfast",
            "export_name": "Z",
        }

        response = client.post(url, payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert not FoodAlias.objects.filter(food=food, alias="Z").exists()

    def test_umlaut_handling_avoids_redundant_alias(self, setup_data):
        """If I rename 'Apfel' to 'Äpfel', no alias should be created because 'Äpfel' already finds 'Apfel'."""
        client, food, day = setup_data
        food.name = "Apfel"
        food.save()

        url = reverse("mealplanfood-list")
        payload = {
            "meal_plan_day": day.id,
            "food": food.id,
            "amount_in_g": 100,
            "meal_type": "breakfast",
            "export_name": "Äpfel",
        }

        response = client.post(url, payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert not FoodAlias.objects.filter(food=food, alias="Äpfel").exists()

    def test_alias_not_created_if_already_exists(self, setup_data):
        """If an alias already exists for that food, we shouldn't fail with IntegrityError (get_or_create handles it)."""
        client, food, day = setup_data
        FoodAlias.objects.create(food=food, alias="Special Fruit")

        url = reverse("mealplanfood-list")
        payload = {
            "meal_plan_day": day.id,
            "food": food.id,
            "amount_in_g": 100,
            "meal_type": "breakfast",
            "export_name": "Special Fruit",
        }

        response = client.post(url, payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert FoodAlias.objects.filter(food=food, alias="Special Fruit").count() == 1

    def test_no_alias_if_case_insensitive_alias_already_exists(self, setup_data):
        """export_name differing only in case from an existing alias must not create a duplicate."""
        client, food, day = setup_data
        FoodAlias.objects.create(food=food, alias="special fruit")

        url = reverse("mealplanfood-list")
        payload = {
            "meal_plan_day": day.id,
            "food": food.id,
            "amount_in_g": 100,
            "meal_type": "breakfast",
            "export_name": "Special Fruit",
        }

        response = client.post(url, payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert FoodAlias.objects.filter(food=food).count() == 1
