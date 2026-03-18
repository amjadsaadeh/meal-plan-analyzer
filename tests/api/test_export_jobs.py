import pytest
from unittest.mock import patch
from rest_framework import status as http_status
from meals.models import BackgroundJob, MealPlan


@pytest.mark.django_db
class TestExportJobCreate:
    def test_requires_authentication(self, api_client):
        """API-04: unauthenticated POST returns 403"""
        response = api_client.post(
            "/api/export-jobs/", {"meal_plan_id": 1}, format="json"
        )
        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_create_returns_201_with_pending_status(self, authenticated_client):
        """API-01: valid POST returns 201, job id, status=pending, progress=0"""
        plan = MealPlan.objects.create(name="Test Plan")
        with patch("meals.views.generate_pdf_task.delay") as mock_delay:
            response = authenticated_client.post(
                "/api/export-jobs/", {"meal_plan_id": plan.pk}, format="json"
            )
        assert response.status_code == http_status.HTTP_201_CREATED
        assert response.data["status"] == "pending"
        assert response.data["progress"] == 0
        assert "id" in response.data
        assert mock_delay.called
        job_id = response.data["id"]
        assert BackgroundJob.objects.filter(pk=job_id).exists()

    def test_create_dispatches_task_with_correct_args(self, authenticated_client):
        """API-01: delay() is called with (str(job.pk), meal_plan_pk)"""
        plan = MealPlan.objects.create(name="Test Plan")
        with patch("meals.views.generate_pdf_task.delay") as mock_delay:
            response = authenticated_client.post(
                "/api/export-jobs/", {"meal_plan_id": plan.pk}, format="json"
            )
        assert response.status_code == http_status.HTTP_201_CREATED
        job_id = response.data["id"]
        mock_delay.assert_called_once_with(str(job_id), plan.pk)

    def test_create_invalid_meal_plan_id(self, authenticated_client):
        """API-01: non-existent meal_plan_id returns 400"""
        with patch("meals.views.generate_pdf_task.delay"):
            response = authenticated_client.post(
                "/api/export-jobs/", {"meal_plan_id": 999999}, format="json"
            )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestExportJobRetrieve:
    def test_requires_authentication(self, api_client):
        """API-04: unauthenticated GET returns 403"""
        job = BackgroundJob.objects.create(task_type="pdf_export", task_kwargs={})
        response = api_client.get(f"/api/export-jobs/{job.pk}/")
        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_retrieve_returns_status_and_progress(self, authenticated_client):
        """API-02: GET returns status, progress, error_message"""
        job = BackgroundJob.objects.create(
            task_type="pdf_export",
            task_kwargs={},
            status=BackgroundJob.Status.RUNNING,
            progress=60,
        )
        response = authenticated_client.get(f"/api/export-jobs/{job.pk}/")
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["status"] == "running"
        assert response.data["progress"] == 60
        assert "error_message" in response.data

    def test_retrieve_invalid_uuid_returns_404(self, authenticated_client):
        """UUID ValueError must return 404 not 500"""
        response = authenticated_client.get("/api/export-jobs/not-a-uuid/")
        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    def test_retrieve_nonexistent_job_returns_404(self, authenticated_client):
        import uuid

        response = authenticated_client.get(f"/api/export-jobs/{uuid.uuid4()}/")
        assert response.status_code == http_status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestExportJobResult:
    def test_requires_authentication(self, api_client):
        """API-04: unauthenticated GET /result/ returns 403"""
        job = BackgroundJob.objects.create(task_type="pdf_export", task_kwargs={})
        response = api_client.get(f"/api/export-jobs/{job.pk}/result/")
        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_result_404_when_status_pending(self, authenticated_client):
        """API-03: 404 when job not done"""
        job = BackgroundJob.objects.create(task_type="pdf_export", task_kwargs={})
        response = authenticated_client.get(f"/api/export-jobs/{job.pk}/result/")
        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    def test_result_404_when_status_running(self, authenticated_client):
        job = BackgroundJob.objects.create(
            task_type="pdf_export",
            task_kwargs={},
            status=BackgroundJob.Status.RUNNING,
        )
        response = authenticated_client.get(f"/api/export-jobs/{job.pk}/result/")
        assert response.status_code == http_status.HTTP_404_NOT_FOUND

    def test_result_404_for_invalid_uuid(self, authenticated_client):
        """UUID ValueError must return 404 not 500"""
        response = authenticated_client.get("/api/export-jobs/not-a-uuid/result/")
        assert response.status_code == http_status.HTTP_404_NOT_FOUND
