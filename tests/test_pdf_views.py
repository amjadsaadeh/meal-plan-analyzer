import pytest
from django.urls import reverse
from rest_framework import status
from meals.models import MealPlan

@pytest.mark.django_db
class TestPDFViews:
    def test_meal_plan_preview_unauthenticated(self, api_client):
        """Test that preview redirects to login if unauthenticated."""
        plan = MealPlan.objects.create(name="Test Plan")
        url = reverse('meal-plan-preview', kwargs={'pk': plan.pk})
        response = api_client.get(url)
        # Django's @login_required decorator returns a 302 redirect to settings.LOGIN_URL
        assert response.status_code == status.HTTP_302_FOUND
        assert 'login' in response.url

    def test_meal_plan_preview_authenticated(self, authenticated_client):
        """Test that preview works if authenticated."""
        plan = MealPlan.objects.create(name="Test Plan")
        url = reverse('meal-plan-preview', kwargs={'pk': plan.pk})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_meal_plan_pdf_unauthenticated(self, api_client):
        """Test that PDF export redirects to login if unauthenticated."""
        plan = MealPlan.objects.create(name="Test Plan")
        url = reverse('meal-plan-pdf', kwargs={'pk': plan.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_302_FOUND
        assert 'login' in response.url

    def test_meal_plan_pdf_authenticated(self, authenticated_client):
        """Test that PDF export works if authenticated."""
        plan = MealPlan.objects.create(name="Test Plan")
        url = reverse('meal-plan-pdf', kwargs={'pk': plan.pk})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/pdf'
