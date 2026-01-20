from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FoodViewSet, MealPlanViewSet, MealPlanDayViewSet, 
    MealPlanFoodViewSet, ThresholdPresetViewSet, index, 
    meal_plan_list, meal_plan_detail, meal_plan_pdf,
    meal_plan_preview
)

router = DefaultRouter()
router.register(r'foods', FoodViewSet)
router.register(r'mealplans', MealPlanViewSet)
router.register(r'mealplan-days', MealPlanDayViewSet)
router.register(r'mealplan-foods', MealPlanFoodViewSet)
router.register(r'threshold-presets', ThresholdPresetViewSet)

urlpatterns = [
    path('', meal_plan_list, name='meal-plan-list'),
    path('meal-plan/new/', meal_plan_detail, name='meal-plan-create'),
    path('meal-plan/<int:pk>/', meal_plan_detail, name='meal-plan-detail'),
    path('meal-plan/<int:pk>/pdf/', meal_plan_pdf, name='meal-plan-pdf'),
    path('meal-plan/<int:pk>/preview/', meal_plan_preview, name='meal-plan-preview'),
    path('search/', index, name='food-search'),
    path('api/', include(router.urls)),
]
