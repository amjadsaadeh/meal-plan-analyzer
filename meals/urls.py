from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from .views import (
    ThrottledLoginView,
    FoodViewSet,
    FoodAliasViewSet,
    MealPlanViewSet,
    MealPlanDayViewSet,
    MealPlanFoodViewSet,
    ThresholdPresetViewSet,
    ExportJobViewSet,
    index,
    meal_plan_list,
    meal_plan_create,
    meal_plan_detail,
    meal_plan_pdf,
    meal_plan_preview,
    meal_plan_preview_content,
    food_database,
    food_editor,
    threshold_preset_list,
    threshold_preset_editor,
)

router = DefaultRouter()
router.register(r"foods", FoodViewSet, basename="food")
router.register(r"food-aliases", FoodAliasViewSet, basename="foodalias")
router.register(r"mealplans", MealPlanViewSet, basename="mealplan")
router.register(r"mealplan-days", MealPlanDayViewSet, basename="mealplanday")
router.register(r"mealplan-foods", MealPlanFoodViewSet, basename="mealplanfood")
router.register(
    r"threshold-presets", ThresholdPresetViewSet, basename="thresholdpreset"
)
router.register(r"export-jobs", ExportJobViewSet, basename="exportjob")

urlpatterns = [
    path(
        "login/",
        ThrottledLoginView.as_view(template_name="meals/login.html.j2"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("", meal_plan_list, name="meal-plan-list"),
    path("meal-plan/", meal_plan_create, name="meal-plan-create"),
    path("meal-plan/<int:pk>/", meal_plan_detail, name="meal-plan-detail"),
    path("meal-plan/<int:pk>/pdf/", meal_plan_pdf, name="meal-plan-pdf"),
    path("meal-plan/<int:pk>/preview/", meal_plan_preview, name="meal-plan-preview"),
    path(
        "meal-plan/<int:pk>/preview/content/",
        meal_plan_preview_content,
        name="meal-plan-preview-content",
    ),
    path("search/", index, name="food-search"),
    path("foods/", food_database, name="food-database"),
    path("foods/<int:pk>/", food_editor, name="food-editor"),
    path("threshold-presets/", threshold_preset_list, name="threshold-preset-list"),
    path(
        "threshold-presets/<int:pk>/",
        threshold_preset_editor,
        name="threshold-preset-editor",
    ),
    path("api/", include(router.urls)),
]
