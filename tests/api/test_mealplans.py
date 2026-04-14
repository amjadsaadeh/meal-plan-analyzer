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

    def test_create_meal_plan_default_name(self, authenticated_client):
        """A plan created without a name gets a default name."""
        response = authenticated_client.post("/api/mealplans/", {}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"]  # non-empty default

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

    def test_list_response_includes_num_pages_and_current_page(
        self, authenticated_client
    ):
        """List response envelope includes num_pages and current_page."""
        response = authenticated_client.get("/api/mealplans/")
        assert response.status_code == status.HTTP_200_OK
        assert "num_pages" in response.data
        assert "current_page" in response.data
        assert response.data["current_page"] == 1

    def test_list_meal_plans_search_filter(self, authenticated_client):
        """?search= filters plans by name (case-insensitive substring)."""
        MealPlan.objects.create(name="Alpha Plan")
        MealPlan.objects.create(name="Beta Plan")

        response = authenticated_client.get("/api/mealplans/?search=alpha")
        assert response.status_code == status.HTTP_200_OK
        names = [p["name"] for p in response.data["results"]]
        assert len(names) == 1
        assert names[0] == "Alpha Plan"

    def test_list_pagination_page_2(self, authenticated_client):
        """?page=2 returns the second page of results with correct envelope fields."""
        for i in range(12):
            MealPlan.objects.create(name=f"Plan {i:02d}")

        r1 = authenticated_client.get("/api/mealplans/?page=1")
        r2 = authenticated_client.get("/api/mealplans/?page=2")
        assert r1.status_code == status.HTTP_200_OK
        assert r2.status_code == status.HTTP_200_OK
        assert len(r1.data["results"]) == 10
        assert len(r2.data["results"]) == 2
        assert r1.data["num_pages"] == 2
        assert r1.data["current_page"] == 1
        assert r2.data["current_page"] == 2

    def test_retrieve_meal_plan(self, authenticated_client):
        """GET on a single plan returns its data."""
        plan = MealPlan.objects.create(name="Retrieve Me")
        response = authenticated_client.get(f"/api/mealplans/{plan.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Retrieve Me"

    def test_patch_meal_plan_name(self, authenticated_client):
        """PATCH updates only the provided fields."""
        plan = MealPlan.objects.create(name="Original Name")
        response = authenticated_client.patch(
            f"/api/mealplans/{plan.id}/", {"name": "Updated Name"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Name"
        plan.refresh_from_db()
        assert plan.name == "Updated Name"

    def test_patch_meal_plan_visible_nutrients(self, authenticated_client):
        """PATCH can update visible_nutrients."""
        plan = MealPlan.objects.create(name="Nutrient Plan")
        response = authenticated_client.patch(
            f"/api/mealplans/{plan.id}/",
            {"visible_nutrients": ["energy_in_kcal", "fat_in_g"]},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "fat_in_g" in response.data["visible_nutrients"]

    def test_patch_meal_plan_unknown_visible_nutrients_stored(
        self, authenticated_client
    ):
        """PATCH with an unknown nutrient key is accepted and stored as-is.
        The model only migrates legacy key names; arbitrary keys are not rejected."""
        plan = MealPlan.objects.create(name="Unknown Nutrient Plan")
        response = authenticated_client.patch(
            f"/api/mealplans/{plan.id}/",
            {"visible_nutrients": ["not_a_real_nutrient"]},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "not_a_real_nutrient" in response.data["visible_nutrients"]

    def test_patch_meal_plan_thresholds(self, authenticated_client):
        """PATCH can set valid thresholds."""
        plan = MealPlan.objects.create(name="Threshold Plan")
        payload = {"thresholds": {"energy_in_kcal": {"min": 1800, "max": 2200}}}
        response = authenticated_client.patch(
            f"/api/mealplans/{plan.id}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.thresholds["energy_in_kcal"]["min"] == 1800

    def test_patch_meal_plan_invalid_thresholds(self, authenticated_client):
        """PATCH with a malformed thresholds structure is rejected."""
        plan = MealPlan.objects.create(name="Bad Threshold Plan")
        # 'min' must be a number or null, not a string
        payload = {"thresholds": {"energy_in_kcal": {"min": "not-a-number"}}}
        response = authenticated_client.patch(
            f"/api/mealplans/{plan.id}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_meal_plan_subtitle(self, authenticated_client):
        """PATCH can set the subtitle field."""
        plan = MealPlan.objects.create(name="Subtitle Plan")
        response = authenticated_client.patch(
            f"/api/mealplans/{plan.id}/", {"subtitle": "A nice subtitle"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["subtitle"] == "A nice subtitle"

    def test_delete_meal_plan(self, authenticated_client):
        """DELETE removes the plan from the database."""
        plan = MealPlan.objects.create(name="To Be Deleted")
        response = authenticated_client.delete(f"/api/mealplans/{plan.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not MealPlan.objects.filter(id=plan.id).exists()

    def test_delete_meal_plan_unauthenticated(self, api_client):
        """DELETE without auth is rejected."""
        plan = MealPlan.objects.create(name="Protected Plan")
        response = api_client.delete(f"/api/mealplans/{plan.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert MealPlan.objects.filter(id=plan.id).exists()

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

    def test_list_response_has_pagination_fields(self, authenticated_client):
        """List response includes pagination envelope fields."""
        response = authenticated_client.get("/api/mealplans/")
        assert response.status_code == status.HTTP_200_OK
        assert "count" in response.data
        assert "results" in response.data
