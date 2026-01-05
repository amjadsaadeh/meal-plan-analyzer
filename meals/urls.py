from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FoodViewSet, MealPlanViewSet, index

router = DefaultRouter()
router.register(r'foods', FoodViewSet)
router.register(r'mealplans', MealPlanViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
