import json
import os
from datetime import timedelta
from urllib.parse import urlparse

import weasyprint
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponse, FileResponse, Http404, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _, get_language
from django.views.decorators.clickjacking import xframe_options_sameorigin
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from ..models import (
    MealPlan,
    MealPlanDay,
    MealPlanFood,
    FoodAlias,
    ALIAS_CACHE_KEY,
    BackgroundJob,
    SiteSettings,
    get_alias_index,
)
from ..nutrients import NUTRIENTS
from ..serializers import (
    MealPlanSerializer,
    MealPlanDaySerializer,
    MealPlanFoodSerializer,
    BackgroundJobCreateSerializer,
    BackgroundJobSerializer,
)
from .food import parse_food_search, get_food_search_query, get_food_ids_by_alias
from ..tasks import generate_pdf_task

# ---------------------------------------------------------------------------
# URL fetcher
# ---------------------------------------------------------------------------


def django_url_fetcher(url, **kwargs):
    """
    Custom URL fetcher for WeasyPrint that resolves static and media URLs
    to local file paths for reliability in production environments.
    Handles absolute URLs and hashed assets.
    """
    parsed_url = urlparse(url)
    url_path = parsed_url.path

    # 1. Resolve static file URLs
    if settings.STATIC_URL and url_path.startswith(settings.STATIC_URL):
        relative_path = url_path.replace(settings.STATIC_URL, "", 1)

        if settings.STATIC_ROOT:
            full_path = os.path.join(settings.STATIC_ROOT, relative_path)
            if os.path.exists(full_path):
                return weasyprint.default_url_fetcher(f"file://{full_path}", **kwargs)

        normalized_path = finders.find(relative_path)
        if normalized_path:
            return weasyprint.default_url_fetcher(f"file://{normalized_path}", **kwargs)

    # 2. Resolve media file URLs
    if settings.MEDIA_URL and url_path.startswith(settings.MEDIA_URL):
        relative_path = url_path.replace(settings.MEDIA_URL, "", 1)
        full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        if os.path.exists(full_path):
            return weasyprint.default_url_fetcher(f"file://{full_path}", **kwargs)

    # 3. Fallback to default fetcher for other URLs (e.g. external fonts)
    return weasyprint.default_url_fetcher(url, **kwargs)


# ---------------------------------------------------------------------------
# Context helper
# ---------------------------------------------------------------------------


def get_meal_plan_context(pk):
    plan = get_object_or_404(MealPlan, pk=pk)
    days = (
        plan.days.filter(removed=False)
        .order_by("creation_date")
        .prefetch_related("mealplanfood_set__food")
    )

    # 1. Define Nutrients
    visible_keys = plan.visible_nutrients

    visible_nutrients = []
    for key, data in NUTRIENTS.items():
        if key in visible_keys or key == "energy_in_kcal":
            visible_nutrients.append(
                {
                    "key": key,
                    "label": data["label"],
                    "unit": data["unit"],
                    "food_key": data["food_key"],
                }
            )

    # 2. Calculate Daily Data
    days_data = []
    total_nutrients_sum = {key: 0.0 for key in NUTRIENTS.keys()}

    breakfast_label = _("Breakfast")
    lunch_label = _("Lunch")
    dinner_label = _("Dinner")
    meal_type_labels = {
        "breakfast": breakfast_label,
        "lunch": lunch_label,
        "dinner": dinner_label,
    }

    for day in days:
        day_info = {
            "name": day.name,
            "meals": {breakfast_label: [], lunch_label: [], dinner_label: []},
        }

        for mpf in day.mealplanfood_set.all():
            factor = mpf.amount_in_g / 100.0

            item_nutrients = {}
            for n in visible_nutrients:
                val = getattr(mpf.food, n["food_key"]) * factor
                item_nutrients[n["key"]] = val
                total_nutrients_sum[n["key"]] += val

            label = meal_type_labels.get(mpf.meal_type, "Other")
            if label in day_info["meals"]:
                day_info["meals"][label].append(
                    {
                        "mpf_id": mpf.id,
                        "food": mpf.food,
                        "export_name": mpf.export_name,
                        "amount_in_g": mpf.amount_in_g,
                        "nutrients": item_nutrients,
                    }
                )

        days_data.append(day_info)

    # 3. Reference Logic & Summary
    summary_nutrients = []
    num_days = len(days) if len(days) > 0 else 1

    for n in visible_nutrients:
        avg_val = total_nutrients_sum[n["key"]] / num_days

        threshold_data = plan.thresholds.get(n["key"])
        if not isinstance(threshold_data, dict):
            threshold_data = {}

        min_val = threshold_data.get("min")
        max_val = threshold_data.get("max")

        if min_val == "":
            min_val = None
        if max_val == "":
            max_val = None

        if min_val is not None:
            min_val = float(min_val)
        if max_val is not None:
            max_val = float(max_val)

        ref_val = None
        threshold_label = ""

        if min_val is not None and max_val is not None:
            ref_val = (min_val + max_val) / 2
            threshold_label = f"{min_val} - {max_val}"
        elif min_val is not None:
            ref_val = min_val
            threshold_label = f"> {min_val}"
        elif max_val is not None:
            ref_val = max_val
            threshold_label = f"< {max_val}"

        percentage = 0
        if ref_val and ref_val > 0:
            percentage = (avg_val / ref_val) * 100

        is_ok = True
        if min_val is not None and avg_val < min_val:
            is_ok = False
        if max_val is not None and avg_val > max_val:
            is_ok = False

        summary_nutrients.append(
            {
                "label": n["label"],
                "unit": n["unit"],
                "value": avg_val,
                "reference_val": ref_val,
                "percentage": int(percentage),
                "threshold_label": threshold_label,
                "is_ok": is_ok,
            }
        )

    all_nutrients = []
    for key, data in NUTRIENTS.items():
        all_nutrients.append(
            {
                "key": key,
                "label": data["label"],
                "unit": data["unit"],
                "food_key": data["food_key"],
            }
        )

    return {
        "plan": plan,
        "days_count": num_days,
        "visible_nutrients": visible_nutrients,
        "all_nutrients": all_nutrients,
        "summary_nutrients": summary_nutrients,
        "days_data": days_data,
        "csrf_token_string": "",
    }


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------


class _MealPlanPagination(PageNumberPagination):
    page_size = 10

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "num_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )


class MealPlanViewSet(viewsets.ModelViewSet):
    queryset = MealPlan.objects.all()
    serializer_class = MealPlanSerializer
    pagination_class = _MealPlanPagination

    def get_queryset(self):
        active_days = MealPlanDay.objects.filter(removed=False).order_by(
            "creation_date"
        )
        qs = MealPlan.objects.prefetch_related(Prefetch("days", queryset=active_days))
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


class MealPlanDayViewSet(viewsets.ModelViewSet):
    queryset = MealPlanDay.objects.filter(removed=False)
    serializer_class = MealPlanDaySerializer


class MealPlanFoodViewSet(viewsets.ModelViewSet):
    queryset = MealPlanFood.objects.all()
    serializer_class = MealPlanFoodSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        self._handle_export_name_alias(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._handle_export_name_alias(instance)

    def _handle_export_name_alias(self, instance):
        """
        Check if the export_name can be found by the current food search.
        If not (or if it doesn't match the current food), add it as an alias.
        """
        from ..models import Food

        export_name = instance.export_name
        if not export_name or len(export_name) < 2:
            return

        _, _, clean_search = parse_food_search(export_name)
        if not clean_search:
            return

        name_query = get_food_search_query(clean_search)
        is_found = Food.objects.filter(name_query).filter(id=instance.food_id).exists()

        if not is_found:
            alias_ids = get_food_ids_by_alias(clean_search)
            if instance.food_id in alias_ids:
                is_found = True

        if not is_found:
            try:
                FoodAlias.objects.get_or_create(
                    food=instance.food,
                    alias=FoodAlias.objects.filter(
                        food=instance.food, alias__iexact=export_name
                    ).values_list("alias", flat=True).first() or export_name,
                )
            except Exception:
                pass
            cache.delete(ALIAS_CACHE_KEY)



class ExportJobViewSet(viewsets.ViewSet):
    """
    POST /api/export-jobs/          — create job + dispatch task
    GET  /api/export-jobs/<id>/     — poll status
    GET  /api/export-jobs/<id>/result/ — download PDF when done
    """

    def create(self, request):
        serializer = BackgroundJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        meal_plan_pk = serializer.validated_data["meal_plan_id"]

        job = BackgroundJob.objects.create(
            task_type="pdf_export",
            task_kwargs={"meal_plan_pk": meal_plan_pk},
            expires_at=timezone.now() + timedelta(hours=24),
        )

        generate_pdf_task.delay(str(job.pk), meal_plan_pk, get_language() or "en")

        return Response(
            BackgroundJobSerializer(job).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            job = BackgroundJob.objects.get(pk=pk)
        except (BackgroundJob.DoesNotExist, ValueError, DjangoValidationError):
            raise Http404
        return Response(BackgroundJobSerializer(job).data)

    @action(detail=True, methods=["get"], url_path="result")
    def result(self, request, pk=None):
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            job = BackgroundJob.objects.get(pk=pk)
        except (BackgroundJob.DoesNotExist, ValueError, DjangoValidationError):
            raise Http404
        if job.status != BackgroundJob.Status.DONE or not job.result_file:
            raise Http404
        return FileResponse(
            job.result_file.open("rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename=os.path.basename(job.result_file.name),
        )


# ---------------------------------------------------------------------------
# Template views
# ---------------------------------------------------------------------------


@login_required
def meal_plan_list(request):
    from django.core.paginator import Paginator
    from django.db.models import Q, Case, When, Value, IntegerField

    search_query = request.GET.get("search", "").strip()
    queryset = MealPlan.objects.all()

    if search_query:
        terms = search_query.split()
        name_query = Q(name__icontains=search_query)
        for term in terms:
            if len(term) >= 2:
                name_query |= Q(name__icontains=term)

        queryset = queryset.filter(name_query)

        queryset = queryset.annotate(
            relevance=Case(
                When(name__iexact=search_query, then=Value(100)),
                When(name__istartswith=search_query, then=Value(50)),
                When(name__icontains=f" {search_query}", then=Value(40)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by("-relevance", "-change_date")
    else:
        queryset = queryset.order_by("-change_date")

    paginator = Paginator(queryset, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "meals/mealplan_list.html.j2",
        {"page_obj": page_obj, "search_query": search_query},
    )


@login_required
@require_http_methods(["POST"])
def meal_plan_create(request):
    with transaction.atomic():
        parent_plan = MealPlan.objects.create(name=_("New Plan"))
        MealPlanDay.objects.create(name=_("Day 1"), meal_plan=parent_plan)
    return JsonResponse(
        {"redirect": reverse("meal-plan-detail", kwargs={"pk": parent_plan.pk})},
        status=201,
    )


@login_required
def meal_plan_detail(request, pk):
    plan = get_object_or_404(MealPlan, pk=pk)

    nutrients_list = [
        {
            "key": key,
            "label": str(data["label"]),
            "unit": data["unit"],
            "food_key": data["food_key"],
            "precision": data.get("precision", 1),
        }
        for key, data in NUTRIENTS.items()
    ]

    i18n = {
        "saved": _("Saved"),
        "unsavedChanges": _("Unsaved changes"),
        "dayPrefix": _("Day"),
        "errorCreatingDay": _("Error creating day"),
        "deleteIngredient": _("Delete Ingredient"),
        "confirmDeleteIngredient": _(
            "Are you sure you want to remove this ingredient?"
        ),
        "errorDeletingRow": _("Error deleting row"),
        "searchFood": _("Search food..."),
        "noResults": _("No results"),
        "codeLabel": _("Code"),
        "aliasBadge": _("alias"),
        "daySummaryOverview": _("Overview"),
        "confirmApplyTemplate": _(
            "Apply this template? The current reference values will be overwritten."
        ),
        "templateSavedSuccess": _("Template saved successfully."),
        "nameTooShort": _("The name must be at least 3 characters long."),
        "checkingAvailability": _("Checking availability..."),
        "nameAlreadyTaken": _("This name is already taken."),
        "validationError": _("Validation error."),
        "savingError": _("Error saving."),
        "networkError": _("Network error while saving."),
        "deleteDay": _("Delete Day"),
        "confirmDeleteDay": _("Do you really want to delete this day?"),
        "cannotBeUndone": _("This action cannot be undone."),
        "cancel": _("Cancel"),
        "delete": _("Delete"),
        "planOverview": _("Plan Overview (Total)"),
        "saveTemplate": _("Save Template"),
        "saveAsTemplate": _("Save as Reference Value Template"),
        "templateName": _("Template name (min. 3 chars)..."),
        "breakfast": _("Breakfast"),
        "lunch": _("Lunch"),
        "dinner": _("Dinner"),
        "addDay": _("Add Day"),
        "selectColumns": _("Select Columns"),
        "referenceValueTemplate": _("Reference Value Template"),
        "searchTemplate": _("Search template..."),
        "ingredient": _("Ingredient"),
        "amountG": _("Amount (g)"),
        "subtotal": _("Subtotal:"),
        "backToPlans": _("Back to Plans"),
        "planNo": _("Plan No."),
        "exportPdf": _("Export PDF"),
        "editName": _("Edit name"),
        "editDayName": _("Edit day name"),
        "deleteDay2": _("Delete day"),
        "columns": _("Columns"),
        "min": _("min"),
        "max": _("max"),
        "syncing": _("Syncing..."),
        "deleting": _("Deleting..."),
        "exportFailed": _("Export failed. Please retry."),
        "retry": _("Retry"),
    }

    return render(
        request,
        "meals/mealplan_detail.html.j2",
        {
            "plan": plan,
            "plan_id": plan.pk,
            "nutrients_json": json.dumps(nutrients_list),
            "i18n_json": json.dumps({k: str(v) for k, v in i18n.items()}),
            "pdf_url": reverse("meal-plan-pdf", args=[plan.pk]),
            "preview_url": reverse("meal-plan-preview", args=[plan.pk]),
            "plan_list_url": reverse("meal-plan-list"),
        },
    )


@login_required
def meal_plan_preview(request, pk):
    plan = get_object_or_404(MealPlan, pk=pk)
    return render(request, "meals/mealplan_preview.html.j2", {"plan": plan})


@login_required
@xframe_options_sameorigin
def meal_plan_preview_content(request, pk):
    from django.templatetags.static import static

    context = get_meal_plan_context(pk)
    site = SiteSettings.get()
    if site.logo:
        context["logo_path"] = site.logo.url
    if site.minilogo:
        context["minilogo_path"] = site.minilogo.url
    else:
        context["minilogo_path"] = static("meals/img/logo.png")
    context["pdf_footer_line_content"] = site.pdf_footer_line_content
    return render(request, "meals/mealplan_pdf.html.j2", context)


@login_required
def meal_plan_pdf(request, pk):
    context = get_meal_plan_context(pk)

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
        logo_disk_path = finders.find("meals/img/logo.png")
        if logo_disk_path:
            context["minilogo_path"] = f"file://{logo_disk_path}"

    context["pdf_footer_line_content"] = site.pdf_footer_line_content

    html_string = render_to_string("meals/mealplan_pdf.html.j2", context)

    html = weasyprint.HTML(
        string=html_string,
        base_url=request.build_absolute_uri(),
        url_fetcher=django_url_fetcher,
    )
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")

    filename_base = "".join(c if ord(c) < 128 else "_" for c in context["plan"].name)
    filename_base = filename_base.replace(" ", "-")

    response["Content-Disposition"] = f'attachment; filename="{filename_base}.pdf"'
    return response
