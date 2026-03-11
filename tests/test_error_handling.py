"""
Tests for 404 and error handling across API endpoints and template views.

Covers:
  - API: nonexistent IDs on all major resources return 404
  - Frontend views: nonexistent meal plan PK returns 404
  - Unauthenticated access to template views redirects to login
  - Logout view is accessible
"""

import pytest
from rest_framework import status
from django.test import Client
from django.contrib.auth.models import User
from meals.models import MealPlan, MealPlanDay, Food

NONEXISTENT_ID = 999999


# ---------------------------------------------------------------------------
# API 404 tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAPI404s:
    def test_get_nonexistent_food(self, authenticated_client):
        response = authenticated_client.get(f"/api/foods/{NONEXISTENT_ID}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_nonexistent_meal_plan(self, authenticated_client):
        response = authenticated_client.get(f"/api/mealplans/{NONEXISTENT_ID}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_nonexistent_meal_plan_day(self, authenticated_client):
        response = authenticated_client.get(f"/api/mealplan-days/{NONEXISTENT_ID}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_nonexistent_meal_plan_food(self, authenticated_client):
        response = authenticated_client.get(f"/api/mealplan-foods/{NONEXISTENT_ID}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_nonexistent_threshold_preset(self, authenticated_client):
        response = authenticated_client.get(f"/api/threshold-presets/{NONEXISTENT_ID}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_nonexistent_meal_plan(self, authenticated_client):
        response = authenticated_client.patch(
            f"/api/mealplans/{NONEXISTENT_ID}/", {"name": "X"}, format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_nonexistent_meal_plan_day(self, authenticated_client):
        response = authenticated_client.delete(f"/api/mealplan-days/{NONEXISTENT_ID}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_soft_deleted_day_not_found_via_api(self, authenticated_client):
        """A day with removed=True is excluded from the queryset → 404."""
        plan = MealPlan.objects.create()
        day = MealPlanDay.objects.create(meal_plan=plan, removed=True)
        response = authenticated_client.get(f"/api/mealplan-days/{day.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Template view 404 / redirect tests
# ---------------------------------------------------------------------------


@pytest.fixture
def logged_in_django_client(db):
    """Standard Django test Client with a logged-in regular user."""
    user = User.objects.create_user(username="viewtester", password="pass")
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestFrontendViews:
    def test_meal_plan_detail_nonexistent_returns_404(self, logged_in_django_client):
        response = logged_in_django_client.get(f"/meal-plan/{NONEXISTENT_ID}/")
        assert response.status_code == 404

    def test_meal_plan_pdf_nonexistent_returns_404(self, logged_in_django_client):
        response = logged_in_django_client.get(f"/meal-plan/{NONEXISTENT_ID}/pdf/")
        assert response.status_code == 404

    def test_meal_plan_preview_nonexistent_returns_404(self, logged_in_django_client):
        response = logged_in_django_client.get(f"/meal-plan/{NONEXISTENT_ID}/preview/")
        assert response.status_code == 404

    def test_unauthenticated_list_redirects_to_login(self):
        client = Client()
        response = client.get("/")
        assert response.status_code == 302
        assert "/login/" in response["Location"]

    def test_unauthenticated_detail_redirects_to_login(self):
        client = Client()
        response = client.get(f"/meal-plan/{NONEXISTENT_ID}/")
        assert response.status_code == 302
        assert "/login/" in response["Location"]

    def test_unauthenticated_food_search_redirects_to_login(self):
        client = Client()
        response = client.get("/search/")
        assert response.status_code == 302
        assert "/login/" in response["Location"]

    def test_meal_plan_list_renders_for_authenticated_user(
        self, logged_in_django_client
    ):
        response = logged_in_django_client.get("/")
        assert response.status_code == 200

    def test_food_search_page_renders_for_authenticated_user(
        self, logged_in_django_client
    ):
        response = logged_in_django_client.get("/search/")
        assert response.status_code == 200

    def test_logout_view_accessible(self, logged_in_django_client):
        response = logged_in_django_client.post("/logout/")
        # Should redirect after logout (302) not error
        assert response.status_code in (200, 302)
