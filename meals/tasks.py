import logging
import unicodedata

import weasyprint
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.template.loader import render_to_string

from meals.models import BackgroundJob

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    soft_time_limit=300,   # raises SoftTimeLimitExceeded after 5 min
    time_limit=360,        # hard kill after 6 min
    name="meals.tasks.generate_pdf_task",
)
def generate_pdf_task(self, job_id: str, meal_plan_pk: int) -> None:
    """Generate a PDF for the given meal plan and store it on the BackgroundJob.

    Progress milestones:
      0  — task starts / status set to RUNNING
      25 — meal plan context loaded
      60 — HTML string rendered
      90 — PDF bytes produced by WeasyPrint
      100 — file saved, status set to DONE
    """
    try:
        # 1. Mark job RUNNING
        BackgroundJob.objects.filter(pk=job_id).update(
            status=BackgroundJob.Status.RUNNING,
            progress=0,
        )

        # 2. Import inside function body to avoid circular imports
        from meals.models import SiteSettings  # noqa: PLC0415
        from meals.views import get_meal_plan_context, django_url_fetcher  # noqa: PLC0415

        # 3. Load meal plan context
        context = get_meal_plan_context(meal_plan_pk)

        # 4. Resolve logo paths as file:// URLs (worker has no HTTP request)
        site = SiteSettings.get()
        if site.logo:
            context["logo_path"] = f"file://{site.logo.path}"
        else:
            logo_disk_path = finders.find("meals/img/logo.png")
            if logo_disk_path:
                context["logo_path"] = f"file://{logo_disk_path}"

        if site.minilogo:
            context["minilogo_path"] = f"file://{site.minilogo.path}"
        else:
            minilogo_disk_path = finders.find("meals/img/logo.png")
            if minilogo_disk_path:
                context["minilogo_path"] = f"file://{minilogo_disk_path}"

        # Milestone 25% — context loaded
        BackgroundJob.objects.filter(pk=job_id).update(progress=25)

        # 5. Render HTML string
        html_string = render_to_string("meals/mealplan_pdf.html.j2", context)

        # Milestone 60% — HTML rendered
        BackgroundJob.objects.filter(pk=job_id).update(progress=60)

        # 6. Generate PDF bytes via WeasyPrint
        html = weasyprint.HTML(
            string=html_string,
            base_url=settings.SITE_BASE_URL,
            url_fetcher=django_url_fetcher,
        )
        pdf_bytes = html.write_pdf()

        # Milestone 90% — PDF bytes produced
        BackgroundJob.objects.filter(pk=job_id).update(progress=90)

        # 7. Build a safe filename from the plan name
        plan_name = context["plan"].name
        # Decompose Unicode, keep only ASCII, replace spaces with hyphens
        ascii_name = (
            unicodedata.normalize("NFKD", plan_name)
            .encode("ascii", errors="ignore")
            .decode("ascii")
        )
        safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in ascii_name).strip("-")
        if not safe_name:
            safe_name = "meal-plan"
        suffix = str(job_id)[:8]
        filename = f"{safe_name}-{suffix}.pdf"

        # 8. Save file and finalise the job
        job = BackgroundJob.objects.get(pk=job_id)
        job.result_file.save(filename, ContentFile(pdf_bytes), save=False)
        job.progress = 100
        job.status = BackgroundJob.Status.DONE
        job.save(update_fields=["result_file", "progress", "status", "updated_at"])

        logger.info("generate_pdf_task completed successfully for job %s", job_id)

    except SoftTimeLimitExceeded:
        logger.warning("generate_pdf_task soft time limit exceeded for job %s", job_id)
        BackgroundJob.objects.filter(pk=job_id).update(
            status=BackgroundJob.Status.FAILED,
            error_message="Task timed out (soft time limit exceeded).",
        )
        # Do NOT re-raise — timeout is expected; Celery should not mark this FAILURE

    except Exception as exc:
        logger.exception("generate_pdf_task failed for job %s", job_id)
        BackgroundJob.objects.filter(pk=job_id).update(
            status=BackgroundJob.Status.FAILED,
            error_message=str(exc)[:1000],
        )
        raise  # re-raise so Celery marks the task as FAILURE in its own state
