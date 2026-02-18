"""
Tests for the /api/mealplan-foods/ endpoint (MealPlanFoodViewSet).

Covers:
  - Authentication guard
  - Create / retrieve / update / delete
  - Serializer read-only fields (food_name, food_bls_code)
  - Unique-together constraint (meal_plan_day, food, meal_type)
  - Invalid meal_type value
  - Cascade delete when the parent MealPlanDay is deleted
"""

import pytest
from rest_framework import status
from meals.models import Food, MealPlan, MealPlanDay, MealPlanFood


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def plan(db):
    return MealPlan.objects.create(name="Test Plan")


@pytest.fixture
def day(plan):
    return MealPlanDay.objects.create(name="Day 1", meal_plan=plan)


@pytest.fixture
def food(db):
    return Food.objects.create(
        bls_code="FOOD001",
        name="Test Banana",
        energy_in_kj_per_100g=371.0,
        energy_in_kcal_per_100g=89.0,
    )


@pytest.fixture
def food2(db):
    return Food.objects.create(
        bls_code="FOOD002",
        name="Test Oats",
        energy_in_kj_per_100g=1628.0,
        energy_in_kcal_per_100g=389.0,
    )


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMealPlanFoodAuth:
    def test_list_unauthenticated(self, api_client):
        response = api_client.get('/api/mealplan-foods/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_unauthenticated(self, api_client, day, food):
        payload = {"meal_plan_day": day.id, "food": food.id, "amount_in_g": 100, "meal_type": "breakfast"}
        response = api_client.post('/api/mealplan-foods/', payload, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMealPlanFoodCRUD:
    def test_create_meal_plan_food(self, authenticated_client, day, food):
        payload = {
            "meal_plan_day": day.id,
            "food": food.id,
            "amount_in_g": 150.0,
            "meal_type": "breakfast",
        }
        response = authenticated_client.post('/api/mealplan-foods/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert MealPlanFood.objects.filter(meal_plan_day=day, food=food).exists()

    def test_create_returns_food_name_and_bls_code(self, authenticated_client, day, food):
        """food_name and food_bls_code are read-only fields populated by the serializer."""
        payload = {
            "meal_plan_day": day.id,
            "food": food.id,
            "amount_in_g": 100.0,
            "meal_type": "lunch",
        }
        response = authenticated_client.post('/api/mealplan-foods/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['food_name'] == "Test Banana"
        assert response.data['food_bls_code'] == "FOOD001"

    def test_list_meal_plan_foods(self, authenticated_client, day, food):
        MealPlanFood.objects.create(meal_plan_day=day, food=food, amount_in_g=200.0, meal_type="dinner")
        response = authenticated_client.get('/api/mealplan-foods/')
        assert response.status_code == status.HTTP_200_OK
        ids = [item['id'] for item in response.data['results']]
        mpf = MealPlanFood.objects.get(meal_plan_day=day, food=food)
        assert mpf.id in ids

    def test_retrieve_meal_plan_food(self, authenticated_client, day, food):
        mpf = MealPlanFood.objects.create(meal_plan_day=day, food=food, amount_in_g=75.0, meal_type="lunch")
        response = authenticated_client.get(f'/api/mealplan-foods/{mpf.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['amount_in_g'] == 75.0
        assert response.data['meal_type'] == "lunch"

    def test_update_amount(self, authenticated_client, day, food):
        mpf = MealPlanFood.objects.create(meal_plan_day=day, food=food, amount_in_g=100.0, meal_type="breakfast")
        response = authenticated_client.patch(
            f'/api/mealplan-foods/{mpf.id}/', {"amount_in_g": 250.0}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        mpf.refresh_from_db()
        assert mpf.amount_in_g == 250.0

    def test_delete_meal_plan_food(self, authenticated_client, day, food):
        mpf = MealPlanFood.objects.create(meal_plan_day=day, food=food, amount_in_g=100.0, meal_type="dinner")
        response = authenticated_client.delete(f'/api/mealplan-foods/{mpf.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not MealPlanFood.objects.filter(pk=mpf.id).exists()

    def test_all_meal_types_accepted(self, authenticated_client, day, food, food2):
        """breakfast, lunch, and dinner are all valid meal_type values."""
        for meal_type, food_obj in [("breakfast", food), ("lunch", food), ("dinner", food)]:
            MealPlanFood.objects.filter(meal_plan_day=day, food=food_obj, meal_type=meal_type).delete()
            payload = {"meal_plan_day": day.id, "food": food_obj.id, "amount_in_g": 100.0, "meal_type": meal_type}
            response = authenticated_client.post('/api/mealplan-foods/', payload, format='json')
            assert response.status_code == status.HTTP_201_CREATED, f"Failed for meal_type={meal_type}"


# ---------------------------------------------------------------------------
# Constraint tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMealPlanFoodConstraints:
    def test_unique_together_constraint(self, authenticated_client, day, food):
        """Duplicate (meal_plan_day, food, meal_type) triplet is rejected."""
        MealPlanFood.objects.create(meal_plan_day=day, food=food, amount_in_g=100.0, meal_type="breakfast")
        payload = {
            "meal_plan_day": day.id,
            "food": food.id,
            "amount_in_g": 200.0,
            "meal_type": "breakfast",
        }
        response = authenticated_client.post('/api/mealplan-foods/', payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_same_food_different_meal_type_allowed(self, authenticated_client, day, food):
        """Same food in the same day but different meal_type is a different record."""
        MealPlanFood.objects.create(meal_plan_day=day, food=food, amount_in_g=100.0, meal_type="breakfast")
        payload = {
            "meal_plan_day": day.id,
            "food": food.id,
            "amount_in_g": 50.0,
            "meal_type": "lunch",
        }
        response = authenticated_client.post('/api/mealplan-foods/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_invalid_meal_type_rejected(self, authenticated_client, day, food):
        """An unrecognised meal_type value returns 400."""
        payload = {
            "meal_plan_day": day.id,
            "food": food.id,
            "amount_in_g": 100.0,
            "meal_type": "brunch",
        }
        response = authenticated_client.post('/api/mealplan-foods/', payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cascade_delete_with_parent_day(self, day, food):
        """Deleting a MealPlanDay cascades to its MealPlanFood records."""
        mpf = MealPlanFood.objects.create(meal_plan_day=day, food=food, amount_in_g=100.0, meal_type="breakfast")
        day.delete()
        assert not MealPlanFood.objects.filter(pk=mpf.id).exists()
