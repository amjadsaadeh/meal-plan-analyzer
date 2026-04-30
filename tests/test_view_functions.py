"""
Tests for Django template views:
  - meal_plan_list: renders, search, unauthenticated redirect
  - meal_plan_detail: pk=None auto-create redirect, existing plan render
  - food_database: renders, unauthenticated redirect
  - food_editor: renders with food pk, unauthenticated redirect
"""

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from meals.models import Food, MealPlan, MealPlanDay

# ---------------------------------------------------------------------------
# Fixture: logged-in Django test client
# ---------------------------------------------------------------------------


@pytest.fixture
def django_client(db):
    user = User.objects.create_user(username="viewuser", password="pass")
    client = Client()
    client.force_login(user)
    return client


# ---------------------------------------------------------------------------
# meal_plan_list view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMealPlanListView:
    def test_renders_for_authenticated_user(self, django_client):
        response = django_client.get(reverse("meal-plan-list"))
        assert response.status_code == 200

    def test_unauthenticated_redirects_to_login(self):
        response = Client().get(reverse("meal-plan-list"))
        assert response.status_code == 302
        assert "/login/" in response["Location"]

    def test_search_filters_results(self, django_client):
        MealPlan.objects.create(name="Alpha Plan")
        MealPlan.objects.create(name="Beta Plan")
        response = django_client.get(reverse("meal-plan-list") + "?search=Alpha")
        assert response.status_code == 200
        # The template context page_obj should contain only Alpha Plan
        page_obj = response.context["page_obj"]
        names = [p.name for p in page_obj]
        assert any("Alpha" in n for n in names)
        assert all("Beta" not in n for n in names)

    def test_search_no_results(self, django_client):
        response = django_client.get(
            reverse("meal-plan-list") + "?search=nonexistentplan99"
        )
        assert response.status_code == 200
        page_obj = response.context["page_obj"]
        assert len(page_obj.object_list) == 0

    def test_search_query_in_context(self, django_client):
        response = django_client.get(reverse("meal-plan-list") + "?search=hello")
        assert response.status_code == 200
        assert response.context["search_query"] == "hello"

    def test_empty_search_returns_all(self, django_client):
        MealPlan.objects.create(name="Plan X")
        MealPlan.objects.create(name="Plan Y")
        response = django_client.get(reverse("meal-plan-list"))
        assert response.status_code == 200
        page_obj = response.context["page_obj"]
        assert page_obj.paginator.count >= 2


# ---------------------------------------------------------------------------
# meal_plan_detail view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMealPlanDetailView:
    def test_unauthenticated_redirects_to_login(self):
        plan = MealPlan.objects.create(name="Private Plan")
        response = Client().get(reverse("meal-plan-detail", kwargs={"pk": plan.pk}))
        assert response.status_code == 302
        assert "/login/" in response["Location"]

    def test_renders_existing_plan(self, django_client):
        plan = MealPlan.objects.create(name="Existing Plan")
        response = django_client.get(
            reverse("meal-plan-detail", kwargs={"pk": plan.pk})
        )
        assert response.status_code == 200
        assert response.context["plan_id"] == plan.pk

    def test_create_via_post_meal_plan_url(self, django_client):
        """POST /meal-plan/ creates a plan+day and returns JSON redirect URL."""
        before_count = MealPlan.objects.count()
        response = django_client.post(reverse("meal-plan-create"))
        assert response.status_code == 201
        assert MealPlan.objects.count() == before_count + 1
        new_plan = MealPlan.objects.order_by("-creation_date").first()
        assert MealPlanDay.objects.filter(meal_plan=new_plan).count() == 1
        data = response.json()
        assert str(new_plan.pk) in data["redirect"]

    def test_detail_404_for_nonexistent_plan(self, django_client):
        response = django_client.get(reverse("meal-plan-detail", kwargs={"pk": 999999}))
        assert response.status_code == 404

    def test_detail_context_contains_nutrients_json(self, django_client):
        plan = MealPlan.objects.create(name="Context Check")
        response = django_client.get(
            reverse("meal-plan-detail", kwargs={"pk": plan.pk})
        )
        assert response.status_code == 200
        assert "nutrients_json" in response.context
        assert "i18n_json" in response.context


# ---------------------------------------------------------------------------
# food_database view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFoodDatabaseView:
    def test_renders_for_authenticated_user(self, django_client):
        response = django_client.get(reverse("food-database"))
        assert response.status_code == 200

    def test_unauthenticated_redirects_to_login(self):
        response = Client().get(reverse("food-database"))
        assert response.status_code == 302
        assert "/login/" in response["Location"]


# ---------------------------------------------------------------------------
# food_editor view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFoodEditorView:
    def test_renders_for_authenticated_user(self, django_client):
        food = Food.objects.create(
            bls_code="TEST01",
            name="Test Food",
            energy_in_kj_per_100g=100.0,
            energy_in_kcal_per_100g=24.0,
        )
        response = django_client.get(reverse("food-editor", kwargs={"pk": food.pk}))
        assert response.status_code == 200

    def test_unauthenticated_redirects_to_login(self):
        food = Food.objects.create(
            bls_code="TEST02",
            name="Test Food 2",
            energy_in_kj_per_100g=100.0,
            energy_in_kcal_per_100g=24.0,
        )
        response = Client().get(reverse("food-editor", kwargs={"pk": food.pk}))
        assert response.status_code == 302
        assert "/login/" in response["Location"]

    def test_context_contains_food_id(self, django_client):
        food = Food.objects.create(
            bls_code="TEST03",
            name="Test Food 3",
            energy_in_kj_per_100g=100.0,
            energy_in_kcal_per_100g=24.0,
        )
        response = django_client.get(reverse("food-editor", kwargs={"pk": food.pk}))
        assert response.status_code == 200
        assert response.context["food_id"] == food.pk

    def test_context_contains_nutrients_and_i18n(self, django_client):
        food = Food.objects.create(
            bls_code="TEST04",
            name="Test Food 4",
            energy_in_kj_per_100g=100.0,
            energy_in_kcal_per_100g=24.0,
        )
        response = django_client.get(reverse("food-editor", kwargs={"pk": food.pk}))
        assert response.status_code == 200
        assert "nutrients_json" in response.context
        assert "i18n_json" in response.context
        assert "food_list_url" in response.context
