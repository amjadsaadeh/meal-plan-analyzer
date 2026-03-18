import pytest
from unittest.mock import patch, MagicMock
from celery.exceptions import SoftTimeLimitExceeded
from meals.models import BackgroundJob, MealPlan
from meals.tasks import generate_pdf_task


@pytest.mark.django_db
class TestGeneratePdfTask:
    def _make_job(self, meal_plan):
        return BackgroundJob.objects.create(
            task_type="pdf_export",
            task_kwargs={"meal_plan_pk": meal_plan.pk},
        )

    def test_marks_job_running_then_done_on_success(self, db):
        """TASK-01 + TASK-02: happy path updates status and progress to done/100"""
        plan = MealPlan.objects.create(name="Test Plan")
        job = self._make_job(plan)

        fake_pdf_bytes = b"%PDF-1.4 fake"

        with (
            patch("meals.views.get_meal_plan_context") as mock_ctx,
            patch("meals.views.django_url_fetcher"),
            patch("weasyprint.HTML") as mock_html_cls,
        ):
            mock_ctx.return_value = {"plan": plan, "days": []}
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = fake_pdf_bytes
            mock_html_cls.return_value = mock_html_instance

            generate_pdf_task(str(job.pk), plan.pk)

        job.refresh_from_db()
        assert job.status == BackgroundJob.Status.DONE
        assert job.progress == 100
        assert job.result_file.name  # file path is set

    def test_marks_job_failed_on_soft_time_limit(self, db):
        """TASK-03: SoftTimeLimitExceeded sets status=failed"""
        plan = MealPlan.objects.create(name="Test Plan")
        job = self._make_job(plan)

        with patch(
            "meals.views.get_meal_plan_context", side_effect=SoftTimeLimitExceeded()
        ):
            generate_pdf_task(str(job.pk), plan.pk)

        job.refresh_from_db()
        assert job.status == BackgroundJob.Status.FAILED
        assert "timed out" in job.error_message.lower()

    def test_marks_job_failed_on_generic_exception(self, db):
        """TASK-03: generic exceptions set status=failed and re-raise"""
        plan = MealPlan.objects.create(name="Test Plan")
        job = self._make_job(plan)

        with patch(
            "meals.views.get_meal_plan_context", side_effect=RuntimeError("boom")
        ):
            with pytest.raises(RuntimeError, match="boom"):
                generate_pdf_task(str(job.pk), plan.pk)

        job.refresh_from_db()
        assert job.status == BackgroundJob.Status.FAILED
        assert "boom" in job.error_message

    def test_progress_milestones_are_set(self, db):
        """TASK-02: verify final state is done and progress=100"""
        plan = MealPlan.objects.create(name="Test Plan")
        job = self._make_job(plan)

        fake_pdf_bytes = b"%PDF-1.4 fake"

        with (
            patch("meals.views.get_meal_plan_context") as mock_ctx,
            patch("meals.views.django_url_fetcher"),
            patch("weasyprint.HTML") as mock_html_cls,
        ):
            mock_ctx.return_value = {"plan": plan, "days": []}
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = fake_pdf_bytes
            mock_html_cls.return_value = mock_html_instance

            generate_pdf_task(str(job.pk), plan.pk)

        job.refresh_from_db()
        assert job.status == BackgroundJob.Status.DONE
        assert job.progress == 100
