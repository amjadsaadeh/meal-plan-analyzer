"""
Tests for the Django admin interface (meals/admin.py).

Uses a superuser via the standard Django test client to verify that:
  - List views for all registered models return HTTP 200
  - Add forms for all registered models render without errors
  - Search on list views functions correctly
  - Change forms for existing objects load without errors
"""

import pytest
from django.contrib.auth.models import User
from django.test import Client
from meals.models import Food, MealPlan, MealPlanDay, ThresholdPreset, SiteSettings


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_client(db):
    """Django test Client logged in as a superuser."""
    superuser = User.objects.create_superuser(
        username='admin_tester', password='adminpass', email='admin@test.com'
    )
    client = Client()
    client.force_login(superuser)
    return client


@pytest.fixture
def sample_food(db):
    return Food.objects.create(
        bls_code="ADM001", name="Admin Test Food",
        energy_in_kj_per_100g=500, energy_in_kcal_per_100g=120,
    )


@pytest.fixture
def sample_plan(db):
    return MealPlan.objects.create(name="Admin Test Plan")


@pytest.fixture
def sample_day(sample_plan):
    return MealPlanDay.objects.create(name="Admin Test Day", meal_plan=sample_plan)


@pytest.fixture
def sample_preset(db):
    return ThresholdPreset.objects.create(
        name="Admin Test Preset", energy_in_kcal_min=1800, energy_in_kcal_max=2400
    )


# ---------------------------------------------------------------------------
# Food admin
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFoodAdmin:
    def test_list_view_loads(self, admin_client):
        response = admin_client.get('/admin/meals/food/')
        assert response.status_code == 200

    def test_add_form_loads(self, admin_client):
        response = admin_client.get('/admin/meals/food/add/')
        assert response.status_code == 200

    def test_change_form_loads(self, admin_client, sample_food):
        response = admin_client.get(f'/admin/meals/food/{sample_food.pk}/change/')
        assert response.status_code == 200

    def test_search_returns_200(self, admin_client, sample_food):
        response = admin_client.get('/admin/meals/food/?q=Admin+Test+Food')
        assert response.status_code == 200

    def test_search_by_bls_code(self, admin_client, sample_food):
        response = admin_client.get('/admin/meals/food/?q=ADM001')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# MealPlan admin
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMealPlanAdmin:
    def test_list_view_loads(self, admin_client):
        response = admin_client.get('/admin/meals/mealplan/')
        assert response.status_code == 200

    def test_add_form_loads(self, admin_client):
        response = admin_client.get('/admin/meals/mealplan/add/')
        assert response.status_code == 200

    def test_change_form_loads(self, admin_client, sample_plan):
        response = admin_client.get(f'/admin/meals/mealplan/{sample_plan.pk}/change/')
        assert response.status_code == 200

    def test_search_by_name(self, admin_client, sample_plan):
        response = admin_client.get('/admin/meals/mealplan/?q=Admin+Test+Plan')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# MealPlanDay admin
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMealPlanDayAdmin:
    def test_list_view_loads(self, admin_client):
        response = admin_client.get('/admin/meals/mealplanday/')
        assert response.status_code == 200

    def test_add_form_loads(self, admin_client):
        response = admin_client.get('/admin/meals/mealplanday/add/')
        assert response.status_code == 200

    def test_change_form_with_inline_loads(self, admin_client, sample_day):
        """The MealPlanDayAdmin has a MealPlanFoodInline — ensure it renders."""
        response = admin_client.get(f'/admin/meals/mealplanday/{sample_day.pk}/change/')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# ThresholdPreset admin
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestThresholdPresetAdmin:
    def test_list_view_loads(self, admin_client):
        response = admin_client.get('/admin/meals/thresholdpreset/')
        assert response.status_code == 200

    def test_add_form_loads(self, admin_client):
        response = admin_client.get('/admin/meals/thresholdpreset/add/')
        assert response.status_code == 200

    def test_change_form_loads(self, admin_client, sample_preset):
        response = admin_client.get(f'/admin/meals/thresholdpreset/{sample_preset.pk}/change/')
        assert response.status_code == 200

    def test_search_by_name(self, admin_client, sample_preset):
        response = admin_client.get('/admin/meals/thresholdpreset/?q=Admin+Test+Preset')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# SiteSettings admin (singleton UX)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSiteSettingsAdmin:
    def test_changelist_redirects_to_change_form(self, admin_client):
        """Visiting the changelist auto-creates the singleton and redirects to its change form."""
        response = admin_client.get('/admin/meals/sitesettings/')
        assert response.status_code == 302
        assert response.url == '/admin/meals/sitesettings/1/change/'

    def test_change_form_loads(self, admin_client):
        SiteSettings.get()  # ensure singleton exists
        response = admin_client.get('/admin/meals/sitesettings/1/change/')
        assert response.status_code == 200

    def test_add_permission_denied_when_instance_exists(self, admin_client):
        """Admins cannot add a second SiteSettings object."""
        SiteSettings.get()
        response = admin_client.get('/admin/meals/sitesettings/add/')
        assert response.status_code == 403

    def test_delete_permission_denied(self, admin_client):
        """Delete is always disabled for SiteSettings."""
        SiteSettings.get()
        response = admin_client.post('/admin/meals/sitesettings/1/delete/')
        assert response.status_code == 403
