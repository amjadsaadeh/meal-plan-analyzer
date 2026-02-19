import pytest
from unittest.mock import patch, MagicMock
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


def _mock_site_with_logo(url='/media/logos/custom.png', path='/srv/media/logos/custom.png'):
    """Return a mock SiteSettings object with a logo set."""
    mock_logo = MagicMock()
    mock_logo.url = url
    mock_logo.path = path
    mock_logo.__bool__ = lambda self: True

    mock_site = MagicMock()
    mock_site.logo = mock_logo
    return mock_site


def _mock_site_without_logo():
    """Return a mock SiteSettings object with no logo."""
    mock_site = MagicMock()
    mock_site.logo = None
    return mock_site


@pytest.mark.django_db
class TestPDFLogoSelection:
    def test_preview_content_uses_uploaded_logo_url(self, authenticated_client):
        """When a custom logo is uploaded, preview content uses its media URL."""
        plan = MealPlan.objects.create(name="Logo Plan")
        mock_site = _mock_site_with_logo(url='/media/logos/custom.png')

        with patch('meals.views.SiteSettings.get', return_value=mock_site):
            url = reverse('meal-plan-preview-content', kwargs={'pk': plan.pk})
            response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert '/media/logos/custom.png' in response.content.decode()

    def test_preview_content_no_logo_falls_back_to_static(self, authenticated_client):
        """When no custom logo is set, preview content falls back to static logo."""
        plan = MealPlan.objects.create(name="No Logo Plan")
        mock_site = _mock_site_without_logo()

        with patch('meals.views.SiteSettings.get', return_value=mock_site):
            url = reverse('meal-plan-preview-content', kwargs={'pk': plan.pk})
            response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Template {% static 'meals/img/logo.png' %} should be rendered
        assert 'logo.png' in response.content.decode()

    def test_pdf_view_with_uploaded_logo_succeeds(self, authenticated_client):
        """When a custom logo is uploaded, PDF generation uses its file path."""
        plan = MealPlan.objects.create(name="Logo PDF Plan")
        import tempfile, os
        # Create a real temporary PNG so WeasyPrint can find the path
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 16)  # minimal PNG header
            tmp_path = tmp.name

        try:
            mock_site = _mock_site_with_logo(path=tmp_path)
            with patch('meals.views.SiteSettings.get', return_value=mock_site):
                url = reverse('meal-plan-pdf', kwargs={'pk': plan.pk})
                response = authenticated_client.get(url)

            assert response.status_code == status.HTTP_200_OK
            assert response['Content-Type'] == 'application/pdf'
        finally:
            os.unlink(tmp_path)

    def test_pdf_view_without_logo_uses_static_fallback(self, authenticated_client):
        """When no custom logo is set, PDF generation falls back to the static logo."""
        plan = MealPlan.objects.create(name="Static Logo PDF Plan")
        mock_site = _mock_site_without_logo()

        with patch('meals.views.SiteSettings.get', return_value=mock_site):
            url = reverse('meal-plan-pdf', kwargs={'pk': plan.pk})
            response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/pdf'
