import re
from django.shortcuts import render
from django.db.models import Q, Case, When, Value, IntegerField, FloatField
from django.utils.translation import gettext as _
from rest_framework import viewsets, filters
from rest_framework.response import Response
from .models import (
    Food, MealPlan, MealPlanDay, MealPlanFood, ThresholdPreset, 
    SiteSettings, get_alias_index, FoodAlias, ALIAS_CACHE_KEY
)
from .serializers import (
    FoodSerializer, MealPlanSerializer, MealPlanDaySerializer,
    MealPlanFoodSerializer, ThresholdPresetSerializer
)
from .nutrients import NUTRIENTS

# ---------------------------------------------------------------------------
# Umlaut helpers
# ---------------------------------------------------------------------------

_UMLAUT_PAIRS = [('a', 'ä'), ('A', 'Ä'), ('o', 'ö'), ('O', 'Ö'), ('u', 'ü'), ('U', 'Ü')]


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
                variant = ''.join(chars)
                if variant != text:
                    variants.add(variant)
        else:
            # Fallback: single-position substitutions only
            for idx, _, umlaut in positions:
                variant = base[:idx] + umlaut + base[idx + 1:]
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
    return render(request, 'meals/index.html.j2')

@login_required
def meal_plan_list(request):
    search_query = request.GET.get('search', '').strip()
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
        ).order_by('-relevance', '-change_date')
    else:
        queryset = queryset.order_by('-change_date')

    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'meals/mealplan_list_vue.html.j2')

@login_required
def meal_plan_detail(request, pk=None):
    if pk is None:
        # Create a new MealPlan and a default MealPlanDay for it
        parent_plan = MealPlan.objects.create(name=_("New Plan"))
        plan_day = MealPlanDay.objects.create(name=_("Day 1"), meal_plan=parent_plan)
        from django.shortcuts import redirect
        return redirect('meal-plan-detail', pk=parent_plan.pk)
    
    plan = get_object_or_404(MealPlan, pk=pk)
    days = plan.days.filter(removed=False).order_by('-creation_date').prefetch_related('mealplanfood_set__food')
    
    meal_types = [
        ('breakfast', _('Breakfast')),
        ('lunch', _('Lunch')),
        ('dinner', _('Dinner')),
    ]
    return render(request, 'meals/mealplan_detail.html.j2', {
        'plan': plan,
        'days': days,
        'meal_types': meal_types,
        'nutrients': NUTRIENTS,
    })

def parse_food_search(search_query):
    """Return (low_energy_intent, high_energy_intent, clean_search) for a raw query."""
    low_energy_intent = bool(re.search(r'\blow\b.*\b(energy|cal|kcal|kj)\b', search_query, re.I))
    high_energy_intent = bool(re.search(r'\bhigh\b.*\b(energy|cal|kcal|kj)\b', search_query, re.I))
    clean_search = re.sub(r'\b(low|high)\b.*\b(energy|cal|kcal|kj)\b', '', search_query, flags=re.I).strip()
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
        normalize_umlauts(t.lower())
        for t in clean_search.split()
        if len(t) >= 2
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


class FoodViewSet(viewsets.ModelViewSet):
    queryset = Food.objects.all()
    serializer_class = FoodSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Food.objects.all()
        search_query = self.request.query_params.get('search', '').strip()

        if len(search_query) < 2:
            return queryset.none() if search_query else queryset

        # 1. Semantic Extraction
        low_energy_intent, high_energy_intent, clean_search = parse_food_search(search_query)

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
        order_params = ['-relevance']
        if low_energy_intent:
            order_params.insert(0, 'energy_in_kcal_per_100g')
        elif high_energy_intent:
            order_params.insert(0, '-energy_in_kcal_per_100g')
        order_params.append('name')

        return queryset.order_by(*order_params)

    def list(self, request, *args, **kwargs):
        """Return foods matching by name/bls_code and additionally by aliases.

        Foods that only appear due to an alias match carry a non-null
        ``matched_alias`` attribute which the serializer exposes so the
        frontend can render an "alias" badge.
        """
        search_query = request.query_params.get('search', '').strip()

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
                        if search_norm in alias_norm or any(t in alias_norm for t in terms_norm):
                            alias_matches[food_id] = alias
                            break

        # Fetch foods that matched only via alias (not already in name results)
        alias_only_ids = set(alias_matches.keys()) - name_food_ids
        alias_only_foods = (
            list(Food.objects.filter(id__in=alias_only_ids).order_by('name'))
            if alias_only_ids else []
        )

        # Annotate: name-matched foods get None, alias-only foods get the alias string
        for food in name_foods:
            food.matched_alias = None
        for food in alias_only_foods:
            food.matched_alias = alias_matches[food.id]

        all_foods = name_foods + alias_only_foods
        serializer = self.get_serializer(all_foods, many=True)
        return Response(serializer.data)

from django.db.models import Prefetch

class MealPlanViewSet(viewsets.ModelViewSet):
    queryset = MealPlan.objects.all()
    serializer_class = MealPlanSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        active_days = MealPlanDay.objects.filter(removed=False)
        return MealPlan.objects.prefetch_related(
            Prefetch('days', queryset=active_days)
        ).all()

class MealPlanDayViewSet(viewsets.ModelViewSet):
    queryset = MealPlanDay.objects.filter(removed=False)
    serializer_class = MealPlanDaySerializer

class MealPlanFoodViewSet(viewsets.ModelViewSet):
    queryset = MealPlanFood.objects.order_by('id')
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
    queryset = ThresholdPreset.objects.order_by('id')
    serializer_class = ThresholdPresetSerializer


from django.http import HttpResponse
from django.template.loader import render_to_string
import weasyprint

def get_meal_plan_context(pk):
    plan = get_object_or_404(MealPlan, pk=pk)
    days = plan.days.filter(removed=False).order_by('creation_date').prefetch_related('mealplanfood_set__food')
    
    # 1. Define Nutrients
    visible_keys = plan.visible_nutrients
    
    visible_nutrients = []
    for key, data in NUTRIENTS.items():
        if key in visible_keys or key == 'energy_in_kcal':
            visible_nutrients.append({
                'key': key,
                'label': data['label'],
                'unit': data['unit'],
                'food_key': data['food_key']
            })
    
    # 2. Calculate Daily Data
    days_data = []
    total_nutrients_sum = {key: 0.0 for key in NUTRIENTS.keys()}
    
    breakfast_label = _('Breakfast')
    lunch_label = _('Lunch')
    dinner_label = _('Dinner')
    meal_type_labels = {
        'breakfast': breakfast_label,
        'lunch': lunch_label,
        'dinner': dinner_label,
    }

    for day in days:
        day_info = {
            'name': day.name,
            'meals': {breakfast_label: [], lunch_label: [], dinner_label: []}
        }
        
        for mpf in day.mealplanfood_set.all():
            factor = mpf.amount_in_g / 100.0
            
            # Calculate nutrients for this item
            item_nutrients = {}
            for n in visible_nutrients:
                val = getattr(mpf.food, n['food_key']) * factor
                item_nutrients[n['key']] = val
                total_nutrients_sum[n['key']] += val
            
            # Add to proper meal category
            label = meal_type_labels.get(mpf.meal_type, 'Other')
            if label in day_info['meals']:
                day_info['meals'][label].append({
                    'mpf_id': mpf.id,
                    'food': mpf.food,
                    'export_name': mpf.export_name,
                    'amount_in_g': mpf.amount_in_g,
                    'nutrients': item_nutrients
                })
        
        days_data.append(day_info)

    # 3. Reference Logic & Summary
    summary_nutrients = []
    num_days = len(days) if len(days) > 0 else 1
    
    for n in visible_nutrients:
        avg_val = total_nutrients_sum[n['key']] / num_days
        
        threshold_data = plan.thresholds.get(n['key'])
        if not isinstance(threshold_data, dict):
            threshold_data = {}
        
        min_val = threshold_data.get('min')
        max_val = threshold_data.get('max')
        
        if min_val == '': min_val = None
        if max_val == '': max_val = None
        
        if min_val is not None: min_val = float(min_val)
        if max_val is not None: max_val = float(max_val)
        
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
            
        summary_nutrients.append({
            'label': n['label'],
            'unit': n['unit'],
            'value': avg_val,
            'reference_val': ref_val,
            'percentage': int(percentage),
            'threshold_label': threshold_label,
            'is_ok': is_ok
        })

    all_nutrients = []
    for key, data in NUTRIENTS.items():
        all_nutrients.append({
            'key': key,
            'label': data['label'],
            'unit': data['unit'],
            'food_key': data['food_key']
        })

    return {
        'plan': plan,
        'days_count': num_days,
        'visible_nutrients': visible_nutrients,
        'all_nutrients': all_nutrients,
        'summary_nutrients': summary_nutrients,
        'days_data': days_data,
        'csrf_token_string': '', # We'll handle CSRF from the request if needed
    }

from django.views.decorators.clickjacking import xframe_options_sameorigin

@login_required
def meal_plan_preview(request, pk):
    plan = get_object_or_404(MealPlan, pk=pk)
    return render(request, 'meals/mealplan_preview.html.j2', {'plan': plan})

@login_required
@xframe_options_sameorigin
def meal_plan_preview_content(request, pk):
    context = get_meal_plan_context(pk)
    site = SiteSettings.get()
    if site.logo:
        context['logo_path'] = site.logo.url
    return render(request, 'meals/mealplan_pdf.html.j2', context)

@login_required
def meal_plan_pdf(request, pk):
    context = get_meal_plan_context(pk)

    site = SiteSettings.get()
    if site.logo:
        context['logo_path'] = f"file://{site.logo.path}"
    else:
        logo_disk_path = finders.find('meals/img/logo.png')
        if logo_disk_path:
            context['logo_path'] = f"file://{logo_disk_path}"

    html_string = render_to_string('meals/mealplan_pdf.html.j2', context)

    html = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="mealplan_{context["plan"].id}.pdf"'
    return response
