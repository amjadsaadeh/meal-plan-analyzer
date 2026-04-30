from .auth import ThrottledLoginView
from .food import (
    FoodViewSet,
    FoodAliasViewSet,
    index,
    food_database,
    food_editor,
    normalize_umlauts,
    _umlaut_search_variants,
    parse_food_search,
    get_food_search_query,
    get_food_ids_by_alias,
)
from ..models import SiteSettings
from .mealplan import (
    MealPlanViewSet,
    MealPlanDayViewSet,
    MealPlanFoodViewSet,
    ExportJobViewSet,
    get_meal_plan_context,
    django_url_fetcher,
    generate_pdf_task,
    meal_plan_list,
    meal_plan_create,
    meal_plan_detail,
    meal_plan_preview,
    meal_plan_preview_content,
    meal_plan_pdf,
)
from .threshold import (
    ThresholdPresetViewSet,
    threshold_preset_list,
    threshold_preset_editor,
)

__all__ = [
    # auth
    "ThrottledLoginView",
    # food
    "FoodViewSet",
    "FoodAliasViewSet",
    "index",
    "food_database",
    "food_editor",
    "normalize_umlauts",
    "_umlaut_search_variants",
    "parse_food_search",
    "get_food_search_query",
    "get_food_ids_by_alias",
    # models re-exported for test patching
    "SiteSettings",
    # mealplan
    "MealPlanViewSet",
    "MealPlanDayViewSet",
    "MealPlanFoodViewSet",
    "ExportJobViewSet",
    "get_meal_plan_context",
    "django_url_fetcher",
    "generate_pdf_task",
    "meal_plan_list",
    "meal_plan_create",
    "meal_plan_detail",
    "meal_plan_preview",
    "meal_plan_preview_content",
    "meal_plan_pdf",
    # threshold
    "ThresholdPresetViewSet",
    "threshold_preset_list",
    "threshold_preset_editor",
]
