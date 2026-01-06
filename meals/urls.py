from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FoodViewSet, MealPlanViewSet, MealPlanFoodViewSet, index, meal_plan_list, meal_plan_detail

router = DefaultRouter()
router.register(r'foods', FoodViewSet)
router.register(r'mealplans', MealPlanViewSet)
router.register(r'mealplan-foods', MealPlanFoodViewSet)

urlpatterns = [
    path('', meal_plan_list, name='meal-plan-list'),
    path('meal-plan/new/', meal_plan_detail, name='meal-plan-create'),
    path('meal-plan/<int:pk>/', meal_plan_detail, name='meal-plan-detail'),
    path('search/', index, name='food-search'),
    path('api/', include(router.urls)),
]
