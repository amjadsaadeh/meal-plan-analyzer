import pytest
from django.urls import reverse
from rest_framework import status
from meals.models import MealPlan, MealPlanDay


@pytest.mark.django_db
class TestMealPlanDayAPI:
    def test_list_active_days(self, authenticated_client):
        """Test that only non-removed days are listed."""
        plan = MealPlan.objects.create(name="Test Plan")
        MealPlanDay.objects.create(name="Active Day", meal_plan=plan, removed=False)
        MealPlanDay.objects.create(name="Removed Day", meal_plan=plan, removed=True)

        url = reverse("mealplanday-list")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Handle pagination
        data = (
            response.data["results"]
            if isinstance(response.data, dict) and "results" in response.data
            else response.data
        )

        # Check that ONLY one day is returned and it's the active one
        assert len(data) == 1
        assert data[0]["name"] == "Active Day"

    def test_list_days_unauthenticated(self, api_client):
        """Unauthenticated request to list days is rejected."""
        url = reverse("mealplanday-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_day(self, authenticated_client):
        """POST creates a new active MealPlanDay."""
        plan = MealPlan.objects.create(name="Plan for Day")
        url = reverse("mealplanday-list")
        response = authenticated_client.post(
            url, {"name": "New Day", "meal_plan": plan.id}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "New Day"
        assert response.data["removed"] is False
        assert MealPlanDay.objects.filter(name="New Day", meal_plan=plan).exists()

    def test_create_day_default_name(self, authenticated_client):
        """POST without a name uses the model default."""
        plan = MealPlan.objects.create(name="Plan for Default Day")
        url = reverse("mealplanday-list")
        response = authenticated_client.post(url, {"meal_plan": plan.id}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"]  # non-empty default

    def test_create_day_unauthenticated(self, api_client):
        """Unauthenticated POST is rejected."""
        plan = MealPlan.objects.create(name="Protected Plan")
        url = reverse("mealplanday-list")
        response = api_client.post(
            url, {"name": "Unauthorized Day", "meal_plan": plan.id}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_day(self, authenticated_client):
        """GET on a single active day returns its data."""
        plan = MealPlan.objects.create(name="Test Plan")
        day = MealPlanDay.objects.create(name="My Day", meal_plan=plan)
        url = reverse("mealplanday-detail", kwargs={"pk": day.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "My Day"

    def test_patch_day_name(self, authenticated_client):
        """PATCH updates the day name."""
        plan = MealPlan.objects.create(name="Test Plan")
        day = MealPlanDay.objects.create(name="Old Name", meal_plan=plan)
        url = reverse("mealplanday-detail", kwargs={"pk": day.id})
        response = authenticated_client.patch(url, {"name": "New Name"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "New Name"
        day.refresh_from_db()
        assert day.name == "New Name"

    def test_soft_delete_day(self, authenticated_client):
        """Test that patching removed=True soft-deletes the day."""
        plan = MealPlan.objects.create(name="Test Plan")
        day = MealPlanDay.objects.create(name="Day to delete", meal_plan=plan)

        url = reverse("mealplanday-detail", kwargs={"pk": day.id})
        response = authenticated_client.patch(url, {"removed": True}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["removed"] is True

        # Verify it's removed from the list
        list_url = reverse("mealplanday-list")
        list_response = authenticated_client.get(list_url)
        list_data = (
            list_response.data["results"]
            if isinstance(list_response.data, dict) and "results" in list_response.data
            else list_response.data
        )
        assert all(d["id"] != day.id for d in list_data)

        # Verify it's still in the DB but marked as removed
        day.refresh_from_db()
        assert day.removed is True

    def test_get_soft_deleted_day_fails(self, authenticated_client):
        """Test that retrieving a soft-deleted day directly returns 404."""
        plan = MealPlan.objects.create(name="Test Plan")
        day = MealPlanDay.objects.create(
            name="Deleted Day", meal_plan=plan, removed=True
        )

        url = reverse("mealplanday-detail", kwargs={"pk": day.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_day_hard(self, authenticated_client):
        """DELETE (hard) removes the day record from the DB."""
        plan = MealPlan.objects.create(name="Test Plan")
        day = MealPlanDay.objects.create(name="Expendable Day", meal_plan=plan)
        url = reverse("mealplanday-detail", kwargs={"pk": day.id})
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not MealPlanDay.objects.filter(id=day.id).exists()
