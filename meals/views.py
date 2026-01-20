import re
from django.shortcuts import render
from django.db.models import Q, Case, When, Value, IntegerField, FloatField
from rest_framework import viewsets, filters
from .models import Food, MealPlan, MealPlanDay, MealPlanFood, ThresholdPreset
from .serializers import (
    FoodSerializer, MealPlanSerializer, MealPlanDaySerializer, 
    MealPlanFoodSerializer, ThresholdPresetSerializer
)

from django.core.paginator import Paginator

def index(request):
    return render(request, 'meals/index.html')

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
    
    return render(request, 'meals/mealplan_list.html', {
        'page_obj': page_obj,
        'search_query': search_query
    })

def meal_plan_detail(request, pk=None):
    if pk is None:
        # Create a new MealPlan and a default MealPlanDay for it
        parent_plan = MealPlan.objects.create(name="Neuer Plan")
        plan_day = MealPlanDay.objects.create(name="Tag 1", meal_plan=parent_plan)
        from django.shortcuts import redirect
        return redirect('meal-plan-detail', pk=parent_plan.pk)
    
    plan = MealPlan.objects.get(pk=pk)
    days = plan.days.all().order_by('-creation_date').prefetch_related('mealplanfood_set__food')
    
    meal_types = [
        ('breakfast', 'Frühstück'),
        ('lunch', 'Mittagessen'),
        ('dinner', 'Abendessen'),
    ]
    return render(request, 'meals/mealplan_detail.html.j2', {
        'plan': plan,
        'days': days,
        'meal_types': meal_types
    })

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
        # We look for intents like "low energy", "high cal", etc.
        low_energy_intent = bool(re.search(r'\blow\b.*\b(energy|cal|kcal|kj)\b', search_query, re.I))
        high_energy_intent = bool(re.search(r'\bhigh\b.*\b(energy|cal|kcal|kj)\b', search_query, re.I))
        
        # Clean the query string from semantic keywords to perform name search
        clean_search = re.sub(r'\b(low|high)\b.*\b(energy|cal|kcal|kj)\b', '', search_query, flags=re.I).strip()
        if not clean_search and (low_energy_intent or high_energy_intent):
            # If user ONLY typed "low energy", we don't filter by name
            clean_search = ""
        elif not clean_search:
            clean_search = search_query

        # 2. Filtering
        if clean_search:
            # Match the whole phrase or individual words
            terms = clean_search.split()
            name_query = Q(name__icontains=clean_search) | Q(bls_code__icontains=clean_search)
            for term in terms:
                if len(term) >= 2:
                    name_query |= Q(name__icontains=term)
            queryset = queryset.filter(name_query)

        # 3. Weighted Relevance Ranking
        # We assign points based on how well the name matches
        queryset = queryset.annotate(
            relevance=Case(
                When(name__iexact=clean_search, then=Value(100)), # Exact match
                When(name__istartswith=clean_search, then=Value(50)), # Starts with
                When(name__icontains=f" {clean_search}", then=Value(40)), # Word starts with
                default=Value(1),
                output_field=IntegerField(),
            )
        )

        # 4. Final Ordering
        order_params = ['-relevance']
        
        if low_energy_intent:
            order_params.insert(0, 'energy_in_kcal_per_100g') # Sort by lowest cal first
        elif high_energy_intent:
            order_params.insert(0, '-energy_in_kcal_per_100g') # Sort by highest cal first
            
        order_params.append('name')
        
        return queryset.order_by(*order_params)

class MealPlanViewSet(viewsets.ModelViewSet):
    queryset = MealPlan.objects.all()
    serializer_class = MealPlanSerializer

class MealPlanDayViewSet(viewsets.ModelViewSet):
    queryset = MealPlanDay.objects.all()
    serializer_class = MealPlanDaySerializer

class MealPlanFoodViewSet(viewsets.ModelViewSet):
    queryset = MealPlanFood.objects.all()
    serializer_class = MealPlanFoodSerializer

class ThresholdPresetViewSet(viewsets.ModelViewSet):
    queryset = ThresholdPreset.objects.all()
    serializer_class = ThresholdPresetSerializer


from django.http import HttpResponse
from django.template.loader import render_to_string
import weasyprint

def meal_plan_pdf(request, pk):
    plan = MealPlan.objects.get(pk=pk)
    days = plan.days.all().order_by('creation_date').prefetch_related('mealplanfood_set__food')
    
    # 1. Define Nutrients
    nutrients_map = [
        {'key': 'energy_in_kcal', 'label': 'Energy', 'unit': 'kcal', 'food_key': 'energy_in_kcal_per_100g'},
        {'key': 'protein', 'label': 'Protein', 'unit': 'g', 'food_key': 'protein_in_g_per_100g'},
        {'key': 'fat', 'label': 'Fat', 'unit': 'g', 'food_key': 'fat_in_g_per_100g'},
        {'key': 'carbohydrate', 'label': 'Carbohydrate', 'unit': 'g', 'food_key': 'carbohydrate_in_g_per_100g'},
        {'key': 'sugar', 'label': 'Sugar', 'unit': 'g', 'food_key': 'sugar_in_g_per_100g'},
        {'key': 'fibre', 'label': 'Fibre', 'unit': 'g', 'food_key': 'fibre_in_g_per_100g'},
        {'key': 'iron', 'label': 'Iron', 'unit': 'mg', 'food_key': 'iron_in_mg_per_100g'},
        {'key': 'omega3', 'label': 'Omega-3', 'unit': 'g', 'food_key': 'omega3_in_g_per_100g'},
        {'key': 'vitc', 'label': 'Vit C', 'unit': 'mg', 'food_key': 'vitc_in_mg_per_100g'},
        {'key': 'magnesium', 'label': 'Magnesium', 'unit': 'mg', 'food_key': 'magnesium_in_mg_per_100g'},
        {'key': 'zinc', 'label': 'Zinc', 'unit': 'mg', 'food_key': 'zinc_in_mg_per_100g'},
        {'key': 'vitb12', 'label': 'Vit B12', 'unit': 'µg', 'food_key': 'vitb12_in_mug_per_100g'},
        {'key': 'vita', 'label': 'Vit A', 'unit': 'µg', 'food_key': 'vita_in_mug_per_100g'},
        {'key': 'calcium', 'label': 'Calcium', 'unit': 'mg', 'food_key': 'calcium_in_mg_per_100g'},
        {'key': 'vitd', 'label': 'Vit D', 'unit': 'µg', 'food_key': 'vitd_in_mug_per_100g'},
    ]
    
    # Only show enabled nutrients + kcal which is always on
    visible_keys = plan.visible_nutrients
    visible_nutrients = [n for n in nutrients_map if n['key'] in visible_keys or n['key'] == 'energy_in_kcal']
    
    # 2. Calculate Daily Data
    days_data = []
    total_nutrients_sum = {n['key']: 0.0 for n in nutrients_map}
    
    meal_type_labels = {
        'breakfast': 'Frühstück',
        'lunch': 'Mittagessen',
        'dinner': 'Abendessen'
    }

    for day in days:
        day_info = {
            'name': day.name,
            'meals': {'Frühstück': [], 'Mittagessen': [], 'Abendessen': []} 
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
                    'food': mpf.food,
                    'amount_in_g': mpf.amount_in_g,
                    'nutrients': item_nutrients
                })
        
        days_data.append(day_info)

    # 3. Reference Logic & Summary
    # Logic:
    # - If only min -> ref = min
    # - If only max -> ref = max
    # - If both -> ref = (min + max) / 2
    # - Color coding: Warning if < min or > max. OK if in between.
    
    summary_nutrients = []
    num_days = len(days) if len(days) > 0 else 1
    
    for n in visible_nutrients:
        avg_val = total_nutrients_sum[n['key']] / num_days
        
        # Determine thresholds
        # Thresholds format in plan.thresholds: "energy_in_kcal_min": val
        # Mapping: map 'energy_in_kcal' (key) to 'energy_in_kcal_min'
        
        # Special case: map 'energy_in_kcal' to stored key 'energy_in_kcal' or similar? 
        # Looking at previous context/ThresholdPreset, keys are likely: "energy_in_kcal_min" etc.
        # But our nutrients_map key for kcal is 'energy_in_kcal'.
        
        base_key = n['key']
        threshold_key_map = {
            'energy_in_kcal': 'kcal',
            'protein_in_g': 'protein',
            'fat_in_g': 'fat',
            'carbohydrate_in_g': 'carbohydrate',
            'fibre_in_g': 'fibre',
            'sugar_in_g': 'sugar',
            'iron_in_mg': 'iron',
            'omega3_in_g': 'omega3',
            'vitc_in_mg': 'vitc',
            'magnesium_in_mg': 'magnesium',
            'zinc_in_mg': 'zinc',
            'vitb12_in_mug': 'vitb12',
            'vita_in_mug': 'vita',
            'calcium_in_mg': 'calcium',
            'vitd_in_mug': 'vitd',
        }
        
        print(base_key)
        threshold_base = threshold_key_map.get(base_key)

        threshold_data = plan.thresholds.get(threshold_base)
        if not isinstance(threshold_data, dict):
            threshold_data = {}
        
        min_val = threshold_data.get('min')
        max_val = threshold_data.get('max')
        
        # Convert explicit None or empty strings to None
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
            
        # Status
        is_ok = True
        if min_val is not None and avg_val < min_val:
            is_ok = False
        if max_val is not None and avg_val > max_val:
            is_ok = False
            
        # Cap percentage for bar (visual only)
        bar_percentage = min(percentage, 100)
        
        summary_nutrients.append({
            'label': n['label'],
            'unit': n['unit'],
            'value': avg_val,
            'reference_val': ref_val,
            'percentage': int(percentage),
            'threshold_label': threshold_label,
            'is_ok': is_ok
        })

    context = {
        'plan': plan,
        'days_count': num_days,
        'visible_nutrients': visible_nutrients,
        'summary_nutrients': summary_nutrients,
        'days_data': days_data,
    }

    html_string = render_to_string('meals/mealplan_pdf.html.j2', context)
    
    html = weasyprint.HTML(string=html_string)
    pdf = html.write_pdf()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="mealplan_{plan.id}.pdf"'
    return response
