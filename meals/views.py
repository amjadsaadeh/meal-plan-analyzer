import re
from django.shortcuts import render
from django.db.models import Q, Case, When, Value, IntegerField, FloatField
from rest_framework import viewsets, filters
from .models import Food, MealPlan, MealPlanDay, MealPlanFood
from .serializers import FoodSerializer, MealPlanSerializer, MealPlanDaySerializer, MealPlanFoodSerializer

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
    days = plan.days.all().order_by('creation_date').prefetch_related('mealplanfood_set__food')
    
    meal_types = [
        ('breakfast', 'Frühstück'),
        ('lunch', 'Mittagessen'),
        ('dinner', 'Abendessen'),
    ]
    return render(request, 'meals/mealplan_detail.html', {
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
