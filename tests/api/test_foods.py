import pytest
from rest_framework import status
from meals.models import Food

@pytest.mark.django_db
class TestFoodAPI:
    def test_list_foods_unauthenticated(self, api_client):
        """Test getting all foods without authentication."""
        response = api_client.get('/api/foods/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_foods_authenticated(self, authenticated_client):
        """Test getting all foods with authentication."""
        response = authenticated_client.get('/api/foods/')
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) == 100

    def test_get_single_food_unauthenticated(self, api_client):
        """Test getting a single food item without authentication."""
        food = Food.objects.first()
        response = api_client.get(f'/api/foods/{food.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_single_food_authenticated(self, authenticated_client):
        """Test getting a single food item with authentication."""
        food = Food.objects.first()
        response = authenticated_client.get(f'/api/foods/{food.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == food.name
        assert response.data['bls_code'] == food.bls_code

    def test_create_food_unauthenticated(self, api_client):
        """Test creating a new food item without authentication."""
        payload = {"bls_code": "NEWFOOD123", "name": "Test Apple"}
        response = api_client.post('/api/foods/', payload, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_food_authenticated(self, authenticated_client):
        """Test creating a new food item with authentication."""
        payload = {
            "bls_code": "NEWFOOD123",
            "name": "Test Apple",
            "energy_in_kj_per_100g": 200,
            "energy_in_kcal_per_100g": 48,
            "protein_in_g_per_100g": 0.3,
            "fat_in_g_per_100g": 0.2,
            "carbohydrate_in_g_per_100g": 10.0,
            "fibre_in_g_per_100g": 2.4,
            "iron_in_mg_per_100g": 0.1,
            "sugar_in_g_per_100g": 10.0,
            "omega3_in_g_per_100g": 0.01,
            "vitc_in_mg_per_100g": 4.6,
            "magnesium_in_mg_per_100g": 5.0,
            "zinc_in_mg_per_100g": 0.04,
            "vitb12_in_mug_per_100g": 0.0,
            "vita_in_mug_per_100g": 3.0,
            "calcium_in_mg_per_100g": 6.0,
            "vitd_in_mug_per_100g": 0.0
        }
        response = authenticated_client.post('/api/foods/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert Food.objects.filter(bls_code="NEWFOOD123").exists()

    def test_search_foods_name_unauthenticated(self, api_client):
        """Test searching for foods without authentication."""
        response = api_client.get('/api/foods/?search=Apfel')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_search_foods_name_authenticated(self, authenticated_client):
        """Test searching for foods by name with authentication."""
        food = Food.objects.get(pk=1)
        search_term = food.name[:10] 
        response = authenticated_client.get(f'/api/foods/?search={search_term}')
        assert response.status_code == status.HTTP_200_OK
        assert any(item['name'] == food.name for item in response.data)

    def test_search_foods_semantic_low_energy_authenticated(self, authenticated_client):
        """Test the 'low energy' semantic search intent with authentication."""
        response = authenticated_client.get('/api/foods/?search=low energy')
        assert response.status_code == status.HTTP_200_OK
        energies = [item['energy_in_kcal_per_100g'] for item in response.data]
        assert energies == sorted(energies)
