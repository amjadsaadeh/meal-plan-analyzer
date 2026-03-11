import pytest
from rest_framework import status
from meals.models import MealPlan, MealPlanDay


@pytest.mark.django_db
class TestMealPlanAPI:
    def test_create_meal_plan_unauthenticated(self, api_client):
        """Test creating a new meal plan without authentication."""
        payload = {"name": "Test Plan 1"}
        response = api_client.post("/api/mealplans/", payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_meal_plan_authenticated(self, authenticated_client):
        """Test creating a new meal plan with authentication."""
        payload = {
            "name": "Test Plan 1",
            "visible_nutrients": ["energy_in_kcal", "protein_in_g"],
            "thresholds": {"energy_in_kcal": {"min": 2000, "max": 2500}},
        }
        response = authenticated_client.post("/api/mealplans/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Test Plan 1"
        assert MealPlan.objects.filter(name="Test Plan 1").exists()

    def test_list_meal_plans_unauthenticated(self, api_client):
        """Test listing meal plans without authentication."""
        response = api_client.get("/api/mealplans/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_meal_plans_authenticated(self, authenticated_client):
        """Test listing meal plans with authentication."""
        MealPlan.objects.create(name="Plan A")
        MealPlan.objects.create(name="Plan B")

        response = authenticated_client.get("/api/mealplans/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 2

    def test_meal_plan_nested_days_filtering(self, authenticated_client):
        """Test that nested days in meal plan are filtered by removed=False."""
        plan = MealPlan.objects.create(name="Nested Test Plan")
        MealPlanDay.objects.create(name="Active Day", meal_plan=plan, removed=False)
        MealPlanDay.objects.create(name="Removed Day", meal_plan=plan, removed=True)

        url = f"/api/mealplans/{plan.id}/"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        days = response.data["days"]
        assert len(days) == 1
        assert days[0]["name"] == "Active Day"
