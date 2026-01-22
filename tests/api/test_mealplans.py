import pytest
from rest_framework import status
from meals.models import MealPlan

@pytest.mark.django_db
class TestMealPlanAPI:
    def test_create_meal_plan(self, api_client):
        """Test creating a new meal plan."""
        payload = {
            "name": "Test Plan 1",
            "visible_nutrients": ["energy_in_kcal", "protein_in_g"],
            "thresholds": {
                "energy_in_kcal": {"min": 2000, "max": 2500}
            }
        }
        response = api_client.post('/api/mealplans/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == "Test Plan 1"
        assert MealPlan.objects.filter(name="Test Plan 1").exists()

    def test_list_meal_plans(self, api_client):
        """Test listing meal plans."""
        MealPlan.objects.create(name="Plan A")
        MealPlan.objects.create(name="Plan B")
        
        response = api_client.get('/api/mealplans/')
        assert response.status_code == status.HTTP_200_OK
        # Check if list is returned (depends on pagination settings, but MealPlanViewSet doesn't override them)
        # Default pagination is PageNumberPagination(100)
        assert response.data['count'] >= 2
