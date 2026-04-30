import re
import json
import secrets

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Case, When, Value, IntegerField
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from ..models import Food, FoodAlias, ALIAS_CACHE_KEY, get_alias_index
from ..nutrients import NUTRIENTS
from ..serializers import FoodSerializer, FoodAliasSerializer

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


# ---------------------------------------------------------------------------
# Food search helpers
# ---------------------------------------------------------------------------


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


def _alias_relevance(alias: str, clean_search: str) -> int:
    """Return a relevance score for an alias match using the same 100/50/40/1 scale as name matches."""
    alias_norm = normalize_umlauts(alias.lower())
    search_norm = normalize_umlauts(clean_search.lower())
    if alias_norm == search_norm:
        return 100
    if alias_norm.startswith(search_norm):
        return 50
    if f" {search_norm}" in alias_norm:
        return 40
    return 1


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------


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

        Both browse (no search) and search responses use the same paginated
        envelope: { count, next, previous, results }.  The page and page_size
        query parameters work for both modes.
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

        # ── Search path ───────────────────────────────────────────────────
        # Get name-based results via the regular queryset
        name_queryset = self.get_queryset()
        name_foods = list(name_queryset)
        name_food_ids = {f.id for f in name_foods}

        # Alias search (Python-side, using the cached index)
        # Both the search term and the stored alias are normalised (ä→a, ö→o,
        # ü→u) before the substring check so that e.g. "Erdapfel" matches the
        # alias "Erdäpfel" and "Möhre" matches the alias "Mohre".
        alias_matches: dict[int, str] = {}  # food_id → best matching alias string
        low_energy_intent = high_energy_intent = False
        clean_search = ""
        if len(search_query) >= 2:
            low_energy_intent, high_energy_intent, clean_search = parse_food_search(
                search_query
            )
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
            food.relevance = _alias_relevance(alias_matches[food.id], clean_search)

        all_foods = name_foods + alias_only_foods
        if low_energy_intent:
            all_foods.sort(
                key=lambda f: (f.energy_in_kcal_per_100g, -f.relevance, f.name)
            )
        elif high_energy_intent:
            all_foods.sort(
                key=lambda f: (-f.energy_in_kcal_per_100g, -f.relevance, f.name)
            )
        else:
            all_foods.sort(key=lambda f: (-f.relevance, f.name))

        # Paginate the assembled list (DRF's paginator accepts any sequence)
        page = self.paginate_queryset(all_foods)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
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
        alias_text = " ".join((request.data.get("alias") or "").split())
        food_id = request.data.get("food")
        if not alias_text:
            return Response({"alias": "This field is required."}, status=400)
        if not food_id:
            return Response({"food": "This field is required."}, status=400)

        food = Food.objects.filter(pk=food_id).first()
        if not food:
            return Response({"food": "Food not found."}, status=400)

        if alias_text.lower() == food.name.lower():
            return Response(
                {"alias": "Alias is identical to the food's own name."}, status=400
            )

        existing = FoodAlias.objects.filter(
            food_id=food_id, alias__iexact=alias_text
        ).first()
        if existing:
            serializer = self.get_serializer(existing)
            return Response(serializer.data, status=200)

        obj = FoodAlias.objects.create(food=food, alias=alias_text)
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=201)


# ---------------------------------------------------------------------------
# Template views
# ---------------------------------------------------------------------------


@login_required
def index(request):
    return render(request, "meals/index.html.j2")


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
        "deleteAliasConfirm": _('Remove alias "{alias}"?'),
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
