import re
import os
import json
import secrets
from django.shortcuts import render
from django.db.models import Q, Case, When, Value, IntegerField, FloatField
from django.urls import reverse
from django.utils.translation import gettext as _
from rest_framework import viewsets, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from .models import (
    Food,
    MealPlan,
    MealPlanDay,
    MealPlanFood,
    ThresholdPreset,
    SiteSettings,
    get_alias_index,
    FoodAlias,
    ALIAS_CACHE_KEY,
)
from .serializers import (
    FoodSerializer,
    FoodAliasSerializer,
    MealPlanSerializer,
    MealPlanDaySerializer,
    MealPlanFoodSerializer,
    ThresholdPresetSerializer,
)
from .nutrients import NUTRIENTS

# ---------------------------------------------------------------------------
# Umlaut helpers
# ---------------------------------------------------------------------------

_UMLAUT_PAIRS = [("a", "ä"), ("A", "Ä"), ("o", "ö"), ("O", "Ö"), ("u", "ü"), ("U", "Ü")]


def normalize_umlauts(text: str) -> str:
    """Fold German umlauts to their ASCII base vowels (ä→a, ö→o, ü→u)."""
    for plain, umlaut in _UMLAUT_PAIRS:
        text = text.replace(umlaut, plain)
    return text


def _umlaut_search_variants(text: str) -> list[str]:
    """Return extra DB search terms covering all umlaut substitution combinations.

    Strategy
    --------
    1. **Normalised form** (ä→a, ö→o, ü→u) – covers the case where the user
       typed WITH umlauts but the stored value uses plain ASCII vowels
       (e.g. "Tomäte" → also searches "Tomate").

    2. **All permutations** of substituting every plain vowel back to its umlaut
       in the fully-normalised base string – covers the case where the user
       typed WITHOUT umlauts but the stored value has them, including words
       with *multiple* umlauts (e.g. "Gemusebruhe" → also searches "Gemüsebrühe"
       by replacing both 'u' positions simultaneously).

    The number of variants is at most 2^n − 1 where n is the count of
    umlaut-substitutable character positions.  For n > 6 the function falls
    back to single-position substitutions to avoid an exponential blow-up
    on pathological inputs (in practice German food names rarely exceed 3–4
    such positions).
    """
    variants: set[str] = set()

    # 1. Fully normalised form (handles user-typed-with-umlaut → plain-in-DB)
    normalised = normalize_umlauts(text)
    if normalised != text:
        variants.add(normalised)

    # 2. Locate every substitutable position in the normalised base
    base = normalised
    positions: list[tuple[int, str, str]] = []  # (index, plain_char, umlaut_char)
    for plain, umlaut in _UMLAUT_PAIRS:
        start = 0
        while True:
            idx = base.find(plain, start)
            if idx == -1:
                break
            positions.append((idx, plain, umlaut))
            start = idx + 1

    if positions:
        n = len(positions)
        base_chars = list(base)
        if n <= 6:
            # Enumerate all 2^n − 1 non-empty substitution masks
            for mask in range(1, 1 << n):
                chars = base_chars[:]
                for bit, (idx, _, umlaut) in enumerate(positions):
                    if mask >> bit & 1:
                        chars[idx] = umlaut
                variant = "".join(chars)
                if variant != text:
                    variants.add(variant)
        else:
            # Fallback: single-position substitutions only
            for idx, _, umlaut in positions:
                variant = base[:idx] + umlaut + base[idx + 1 :]
                if variant != text:
                    variants.add(variant)

    variants.discard(text)
    return list(variants)


from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.staticfiles import finders
from django.shortcuts import get_object_or_404


@login_required
def index(request):
    return render(request, "meals/index.html.j2")


@login_required
def meal_plan_list(request):
    search_query = request.GET.get("search", "").strip()
    queryset = MealPlan.objects.all()

    if search_query:
        # Semantic/Fuzzy Search logic (simplified for names)
        terms = search_query.split()
        name_query = Q(name__icontains=search_query)
        for term in terms:
            if len(term) >= 2:
                name_query |= Q(name__icontains=term)

        queryset = queryset.filter(name_query)

        # Weighted Relevance Ranking
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
def meal_plan_detail(request, pk=None):
    if pk is None:
        # Create a new MealPlan and a default MealPlanDay for it
        parent_plan = MealPlan.objects.create(name=_("New Plan"))
        plan_day = MealPlanDay.objects.create(name=_("Day 1"), meal_plan=parent_plan)
        from django.shortcuts import redirect

        return redirect("meal-plan-detail", pk=parent_plan.pk)

    import json
    from django.urls import reverse

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


def parse_food_search(search_query):
    """Return (low_energy_intent, high_energy_intent, clean_search) for a raw query."""
    low_energy_intent = bool(
        re.search(r"\blow\b.*\b(energy|cal|kcal|kj)\b", search_query, re.I)
    )
    high_energy_intent = bool(
        re.search(r"\bhigh\b.*\b(energy|cal|kcal|kj)\b", search_query, re.I)
    )
    clean_search = re.sub(
        r"\b(low|high)\b.*\b(energy|cal|kcal|kj)\b", "", search_query, flags=re.I
    ).strip()
    if not clean_search and not (low_energy_intent or high_energy_intent):
        clean_search = search_query
    return low_energy_intent, high_energy_intent, clean_search


def get_food_search_query(clean_search):
    """Return a Q object for filtering foods by name, bls_code, and umlaut variants."""
    if not clean_search:
        return Q()
    terms = clean_search.split()
    name_query = Q(name__icontains=clean_search) | Q(bls_code__icontains=clean_search)
    for term in terms:
        if len(term) >= 2:
            name_query |= Q(name__icontains=term)

    all_variants: set[str] = set(_umlaut_search_variants(clean_search))
    for term in terms:
        all_variants.update(_umlaut_search_variants(term))
    for variant in all_variants:
        if len(variant) >= 2:
            name_query |= Q(name__icontains=variant) | Q(bls_code__icontains=variant)
    return name_query


def get_food_ids_by_alias(clean_search):
    """Return a set of food IDs that match the search query via their aliases."""
    if not clean_search or len(clean_search) < 2:
        return set()

    search_norm = normalize_umlauts(clean_search.lower())
    terms_norm = [
        normalize_umlauts(t.lower()) for t in clean_search.split() if len(t) >= 2
    ]
    alias_index = get_alias_index()
    matched_ids = set()
    for food_id, aliases in alias_index.items():
        for alias in aliases:
            alias_norm = normalize_umlauts(alias.lower())
            if search_norm in alias_norm or any(t in alias_norm for t in terms_norm):
                matched_ids.add(food_id)
                break
    return matched_ids


class _FoodBrowsePagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500


class FoodViewSet(viewsets.ModelViewSet):
    queryset = Food.objects.all()
    serializer_class = FoodSerializer
    pagination_class = _FoodBrowsePagination

    def get_queryset(self):
        queryset = Food.objects.all()
        search_query = self.request.query_params.get("search", "").strip()

        if len(search_query) < 2:
            return queryset.none() if search_query else queryset

        # 1. Semantic Extraction
        low_energy_intent, high_energy_intent, clean_search = parse_food_search(
            search_query
        )

        # 2. Filtering by name / bls_code (with umlaut-tolerant variants)
        if clean_search:
            name_query = get_food_search_query(clean_search)
            queryset = queryset.filter(name_query)

        # 3. Weighted Relevance Ranking
        queryset = queryset.annotate(
            relevance=Case(
                When(name__iexact=clean_search, then=Value(100)),
                When(name__istartswith=clean_search, then=Value(50)),
                When(name__icontains=f" {clean_search}", then=Value(40)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )

        # 4. Final Ordering
        order_params = ["-relevance"]
        if low_energy_intent:
            order_params.insert(0, "energy_in_kcal_per_100g")
        elif high_energy_intent:
            order_params.insert(0, "-energy_in_kcal_per_100g")
        order_params.append("name")

        return queryset.order_by(*order_params)

    def list(self, request, *args, **kwargs):
        """Return foods matching by name/bls_code and additionally by aliases.

        Foods that only appear due to an alias match carry a non-null
        ``matched_alias`` attribute which the serializer exposes so the
        frontend can render an "alias" badge.

        When no search query is provided the response is paginated (100/page)
        using standard DRF page-number pagination.  When a search query is
        given all matching results are returned without pagination (existing
        behaviour, used by the meal-plan food-search dropdown).
        """
        search_query = request.query_params.get("search", "").strip()

        if not search_query:
            # ── Paginated browse (no search) ──────────────────────────────
            queryset = Food.objects.all().order_by("name")
            page = self.paginate_queryset(queryset)
            if page is not None:
                for food in page:
                    food.matched_alias = None
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            # Fallback (pagination disabled) — return everything
            for food in queryset:
                food.matched_alias = None
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        # ── Search path (original behaviour) ──────────────────────────────
        # Get name-based results via the regular queryset
        name_queryset = self.get_queryset()
        name_foods = list(name_queryset)
        name_food_ids = {f.id for f in name_foods}

        # Alias search (Python-side, using the cached index)
        # Both the search term and the stored alias are normalised (ä→a, ö→o,
        # ü→u) before the substring check so that e.g. "Erdapfel" matches the
        # alias "Erdäpfel" and "Möhre" matches the alias "Mohre".
        alias_matches: dict[int, str] = {}  # food_id → best matching alias string
        if len(search_query) >= 2:
            _, _, clean_search = parse_food_search(search_query)
            if clean_search:
                search_norm = normalize_umlauts(clean_search.lower())
                terms_norm = [
                    normalize_umlauts(t.lower())
                    for t in clean_search.split()
                    if len(t) >= 2
                ]
                alias_index = get_alias_index()
                for food_id, aliases in alias_index.items():
                    for alias in aliases:
                        alias_norm = normalize_umlauts(alias.lower())
                        if search_norm in alias_norm or any(
                            t in alias_norm for t in terms_norm
                        ):
                            alias_matches[food_id] = alias
                            break

        # Fetch foods that matched only via alias (not already in name results)
        alias_only_ids = set(alias_matches.keys()) - name_food_ids
        alias_only_foods = (
            list(Food.objects.filter(id__in=alias_only_ids).order_by("name"))
            if alias_only_ids
            else []
        )

        # Annotate: name-matched foods get None, alias-only foods get the alias string
        for food in name_foods:
            food.matched_alias = None
        for food in alias_only_foods:
            food.matched_alias = alias_matches[food.id]

        all_foods = name_foods + alias_only_foods
        serializer = self.get_serializer(all_foods, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        food = self.get_object()
        food.matched_alias = None
        serializer = self.get_serializer(food)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        name = request.data.get("name", "").strip()
        if not name:
            return Response({"name": "This field is required."}, status=400)
        for _ in range(10):
            code = f"custom_{secrets.token_hex(4)}"
            if not Food.objects.filter(bls_code=code).exists():
                break
        food = Food.objects.create(
            name=name,
            bls_code=code,
            data_source="custom",
            energy_in_kj_per_100g=0.0,
            energy_in_kcal_per_100g=0.0,
        )
        food.matched_alias = None
        serializer = self.get_serializer(food)
        return Response(serializer.data, status=201)

    def update(self, request, *args, **kwargs):
        food = self.get_object()
        if food.data_source != "custom":
            return Response(
                {"detail": "Only custom foods can be edited."},
                status=403,
            )

        if (
            "energy_in_kj_per_100g" in request.data
            and "energy_in_kcal_per_100g" in request.data
        ):
            return Response(
                {
                    "detail": "Cannot set both energy_in_kj_per_100g and energy_in_kcal_per_100g at the same time."
                },
                status=400,
            )

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        food = self.get_object()
        if food.data_source != "custom":
            return Response(
                {"detail": "Only custom foods can be deleted."},
                status=403,
            )
        return super().destroy(request, *args, **kwargs)


from django.db.models import Prefetch


class FoodAliasViewSet(viewsets.ModelViewSet):
    """CRUD for FoodAlias records. Filter by food with ?food=<id>."""

    serializer_class = FoodAliasSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = FoodAlias.objects.all()
        food_id = self.request.query_params.get("food")
        if food_id:
            qs = qs.filter(food_id=food_id)
        return qs.order_by("alias")

    def create(self, request, *args, **kwargs):
        alias_text = (request.data.get("alias") or "").strip()
        food_id = request.data.get("food")
        if not alias_text:
            return Response({"alias": "This field is required."}, status=400)
        if not food_id:
            return Response({"food": "This field is required."}, status=400)
        obj, created = FoodAlias.objects.get_or_create(
            food_id=food_id, alias=alias_text
        )
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=201 if created else 200)


class MealPlanViewSet(viewsets.ModelViewSet):
    queryset = MealPlan.objects.all()
    serializer_class = MealPlanSerializer

    def get_queryset(self):
        active_days = MealPlanDay.objects.filter(removed=False).order_by(
            "creation_date"
        )
        return MealPlan.objects.prefetch_related(
            Prefetch("days", queryset=active_days)
        ).all()


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
        from django.core.cache import cache

        export_name = instance.export_name
        if not export_name or len(export_name) < 2:
            return

        _, _, clean_search = parse_food_search(export_name)
        if not clean_search:
            return

        # 1. check if the export name can be found by name/bls search
        name_query = get_food_search_query(clean_search)
        is_found = Food.objects.filter(name_query).filter(id=instance.food_id).exists()

        # 2. if not found, check alias search
        if not is_found:
            alias_ids = get_food_ids_by_alias(clean_search)
            if instance.food_id in alias_ids:
                is_found = True

        # 3. if still not found, add as alias and invalidate cache
        if not is_found:
            FoodAlias.objects.get_or_create(food=instance.food, alias=export_name)
            # Signal handles invalidation, but we do it explicitly as requested
            cache.delete(ALIAS_CACHE_KEY)


class ThresholdPresetViewSet(viewsets.ModelViewSet):
    queryset = ThresholdPreset.objects.all()
    serializer_class = ThresholdPresetSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


from django.http import HttpResponse
from django.template.loader import render_to_string
import weasyprint


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

            # Calculate nutrients for this item
            item_nutrients = {}
            for n in visible_nutrients:
                val = getattr(mpf.food, n["food_key"]) * factor
                item_nutrients[n["key"]] = val
                total_nutrients_sum[n["key"]] += val

            # Add to proper meal category
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
        "csrf_token_string": "",  # We'll handle CSRF from the request if needed
    }


from django.views.decorators.clickjacking import xframe_options_sameorigin


@login_required
def meal_plan_preview(request, pk):
    plan = get_object_or_404(MealPlan, pk=pk)
    return render(request, "meals/mealplan_preview.html.j2", {"plan": plan})


@login_required
@xframe_options_sameorigin
def meal_plan_preview_content(request, pk):
    context = get_meal_plan_context(pk)
    site = SiteSettings.get()
    if site.logo:
        context["logo_path"] = site.logo.url
    if site.minilogo:
        context["minilogo_path"] = site.minilogo.url
    else:
        from django.templatetags.static import static

        context["minilogo_path"] = static("meals/img/logo.png")
    return render(request, "meals/mealplan_pdf.html.j2", context)


from urllib.parse import urlparse


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
        # Extract the relative path within static directory
        relative_path = url_path.replace(settings.STATIC_URL, "", 1)

        # In production with hashed assets, first check STATIC_ROOT
        if settings.STATIC_ROOT:
            full_path = os.path.join(settings.STATIC_ROOT, relative_path)
            if os.path.exists(full_path):
                return weasyprint.default_url_fetcher(f"file://{full_path}", **kwargs)

        # Fallback to staticfiles finders (useful for development or if not in STATIC_ROOT)
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

    html_string = render_to_string("meals/mealplan_pdf.html.j2", context)

    html = weasyprint.HTML(
        string=html_string,
        base_url=request.build_absolute_uri(),
        url_fetcher=django_url_fetcher,
    )
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")

    # Sanitize filename: replace non-ASCII with '_' and spaces with '-'
    filename_base = "".join(c if ord(c) < 128 else "_" for c in context["plan"].name)
    filename_base = filename_base.replace(" ", "-")

    response["Content-Disposition"] = f'attachment; filename="{filename_base}.pdf"'
    return response


@login_required
def food_database(request):
    return render(request, "meals/food_database.html.j2", {})


@login_required
def food_editor(request, pk):
    nutrients_list = [
        {
            "key": key,
            "label": str(meta["label"]),
            "unit": meta["unit"],
            "food_key": meta["food_key"],
            "precision": meta["precision"],
        }
        for key, meta in NUTRIENTS.items()
    ]
    i18n = {
        "saved": _("Saved"),
        "saving": _("Saving…"),
        "error": _("Error saving"),
        "backToList": _("Food Database"),
        "readonlyHint": _(
            "BLS data is read-only. Click the copy button to copy a value."
        ),
        "copiedToClipboard": _("Copied!"),
        "customBadge": _("Custom"),
        "blsBadge": _("BLS"),
        "networkError": _("Network error"),
        "notFound": _("Food not found."),
        "energyKj": _("Energy (kJ)"),
        "energyKcal": _("Energy (kcal)"),
        "name": _("Name"),
        "nameLabel": _("Name"),
        "energy": _("Energy"),
        "macronutrients": _("Macronutrients"),
        "vitamins": _("Vitamins"),
        "aliases": _("Aliases"),
        "aliasInputPlaceholder": _("Add alias…"),
        "addAlias": _("Add"),
        "deleteAliasConfirm": _("Remove alias \"{alias}\"?"),
        "aliasAlreadyExists": _("This alias already exists."),
        "minerals": _("Minerals"),
    }
    return render(
        request,
        "meals/food_editor.html.j2",
        {
            "food_id": pk,
            "nutrients_json": json.dumps(nutrients_list),
            "i18n_json": json.dumps({k: str(v) for k, v in i18n.items()}),
            "food_list_url": reverse("food-database"),
        },
    )
