from django.contrib import admin
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import Food, FoodAlias, MealPlan, MealPlanDay, MealPlanFood, ThresholdPreset, SiteSettings

@admin.register(ThresholdPreset)
class ThresholdPresetAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class FoodAliasInline(admin.TabularInline):
    model = FoodAlias
    extra = 1
    fields = ('alias',)


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
    inlines = [FoodAliasInline]


@admin.register(FoodAlias)
class FoodAliasAdmin(admin.ModelAdmin):
    list_display = ('alias', 'food')
    search_fields = ('alias', 'food__name', 'food__bls_code')
    raw_id_fields = ('food',)

class MealPlanFoodInline(admin.TabularInline):
    model = MealPlanFood
    extra = 1

class MealPlanDayInline(admin.TabularInline):
    model = MealPlanDay
    extra = 1

@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'creation_date', 'change_date')
    inlines = [MealPlanDayInline]
    search_fields = ('name',)

@admin.register(MealPlanDay)
class MealPlanDayAdmin(admin.ModelAdmin):
    list_display = ('name', 'meal_plan', 'creation_date', 'change_date')
    inlines = [MealPlanFoodInline]
    search_fields = ('name',)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Redirect the list view directly to the single settings object
        obj = SiteSettings.get()
        return HttpResponseRedirect(
            reverse('admin:meals_sitesettings_change', args=[obj.pk])
        )
