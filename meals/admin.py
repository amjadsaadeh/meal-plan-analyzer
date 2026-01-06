from django.contrib import admin
from .models import Food, MealPlan, MealPlanFood

@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'bls_code', 
        'energy_in_kcal_per_100g', 
        'protein_in_g_per_100g', 
        'fat_in_g_per_100g', 
        'fibre_in_g_per_100g', 
        'iron_in_mg_per_100g', 
        'sugar_in_g_per_100g'
    )
    search_fields = ('name', 'bls_code')

class MealPlanFoodInline(admin.TabularInline):
    model = MealPlanFood
    extra = 1

@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'creation_date', 'change_date')
    inlines = [MealPlanFoodInline]
    search_fields = ('name',)
