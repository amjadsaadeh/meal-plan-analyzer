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

    def test_meal_plan_pdf_filename_sanitization(self, authenticated_client):
        """Test that the PDF filename is correctly sanitized."""
        plan = MealPlan.objects.create(name="Müsli Frühstück")
        url = reverse('meal-plan-pdf', kwargs={'pk': plan.pk})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Disposition'] == 'attachment; filename="M_sli-Fr_hst_ck.pdf"'


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


@pytest.mark.django_db
class TestPDFStylingIntegrity:
    def test_django_url_fetcher_resolves_static(self):
        """Verify that relative static URLs are correctly mapped to local file paths via finder."""
        from meals.views import django_url_fetcher
        from django.conf import settings

        # Mock finders.find to return a specific path
        with patch('django.contrib.staticfiles.finders.find', return_value='/tmp/test.css'):
            static_url = settings.STATIC_URL + 'test.css'
            with patch('weasyprint.default_url_fetcher') as mock_fetcher:
                django_url_fetcher(static_url)
                mock_fetcher.assert_called_with('file:///tmp/test.css')

    def test_django_url_fetcher_resolves_absolute_static_url(self):
        """Verify that absolute static URLs are correctly mapped to local file paths."""
        from meals.views import django_url_fetcher
        from django.conf import settings

        # Simulate absolute URL from production
        absolute_url = 'https://example.com' + settings.STATIC_URL + 'test.css'
        
        with patch('django.contrib.staticfiles.finders.find', return_value='/tmp/test.css'):
            with patch('weasyprint.default_url_fetcher') as mock_fetcher:
                django_url_fetcher(absolute_url)
                mock_fetcher.assert_called_with('file:///tmp/test.css')

    def test_django_url_fetcher_resolves_hashed_static_url(self):
        """Verify that hashed assets are correctly resolved from STATIC_ROOT."""
        from meals.views import django_url_fetcher
        from django.conf import settings
        import os

        # Mock STATIC_ROOT
        with patch('django.conf.settings.STATIC_ROOT', '/tmp/static'):
            hashed_filename = 'pdf.9bca20cc370d.css'
            url = settings.STATIC_URL + 'meals/scss/' + hashed_filename
            expected_path = os.path.join('/tmp/static', 'meals/scss/', hashed_filename)
            
            with patch('os.path.exists', return_value=True):
                with patch('weasyprint.default_url_fetcher') as mock_fetcher:
                    django_url_fetcher(url)
                    mock_fetcher.assert_called_with(f'file://{expected_path}')

    def test_django_url_fetcher_resolves_media(self):
        """Verify that media URLs are correctly mapped to local file paths."""
        from meals.views import django_url_fetcher
        from django.conf import settings
        import os

        media_url = settings.MEDIA_URL + 'test.png'
        expected_path = os.path.join(settings.MEDIA_ROOT, 'test.png')
        
        with patch('os.path.exists', return_value=True):
            with patch('weasyprint.default_url_fetcher') as mock_fetcher:
                django_url_fetcher(media_url)
                mock_fetcher.assert_called_with(f'file://{expected_path}')

    def test_django_url_fetcher_fallback(self):
        """Verify that non-static/media URLs use the default fetcher."""
        from meals.views import django_url_fetcher
        
        external_url = 'https://fonts.googleapis.com/css?family=Outfit'
        with patch('weasyprint.default_url_fetcher') as mock_fetcher:
            django_url_fetcher(external_url)
            mock_fetcher.assert_called_with(external_url)

    def test_meal_plan_pdf_uses_custom_fetcher(self, authenticated_client):
        """Verify that meal_plan_pdf view passes the custom fetcher to WeasyPrint."""
        from meals.views import django_url_fetcher
        from meals.models import MealPlan
        plan = MealPlan.objects.create(name="Fetcher Test")
        url = reverse('meal-plan-pdf', kwargs={'pk': plan.pk})
        
        with patch('weasyprint.HTML') as mock_html:
            authenticated_client.get(url)
            # Check if url_fetcher argument was passed correctly
            kwargs = mock_html.call_args.kwargs
            assert kwargs.get('url_fetcher') == django_url_fetcher
