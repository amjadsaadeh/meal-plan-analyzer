import pytest
from django.urls import reverse
from rest_framework import status
from meals.models import MealPlan, MealPlanDay

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

    def test_meal_plan_pdf_filters_removed_days(self, authenticated_client):
        """Test that PDF export only contains non-removed days."""
        plan = MealPlan.objects.create(name="PDF Filter Plan")
        MealPlanDay.objects.create(name="Active Day", meal_plan=plan, removed=False)
        MealPlanDay.objects.create(name="Removed Day", meal_plan=plan, removed=True)
        
        url = reverse('meal-plan-pdf', kwargs={'pk': plan.pk})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # We can't easily check PDF content here without more tools, but we can check the context if we test the content view
        
        content_url = reverse('meal-plan-preview-content', kwargs={'pk': plan.pk})
        content_response = authenticated_client.get(content_url)
        assert content_response.status_code == status.HTTP_200_OK
        assert "Active Day" in content_response.content.decode()
        assert "Removed Day" not in content_response.content.decode()
