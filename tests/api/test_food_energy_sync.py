import pytest
from rest_framework import status
from meals.models import Food


@pytest.mark.django_db
class TestFoodEnergySyncAPI:
    def test_update_food_sync_kcal_to_kj(self, authenticated_client):
        """Test updating a food with only kcal; kj should be updated."""
        food = Food.objects.create(
            name="Update Food",
            bls_code="UPDATE001",
            data_source="custom",
            energy_in_kcal_per_100g=0,
            energy_in_kj_per_100g=0,
        )
        payload = {"energy_in_kcal_per_100g": 200.0}
        response = authenticated_client.patch(
            f"/api/foods/{food.id}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_200_OK

        food.refresh_from_db()
        # 200 * 4.184 = 836.8
        assert food.energy_in_kcal_per_100g == 200.0
        assert food.energy_in_kj_per_100g == 836.8

    def test_update_food_sync_kj_to_kcal(self, authenticated_client):
        """Test updating a food with only kj; kcal should be updated."""
        food = Food.objects.create(
            name="Update Food 2",
            bls_code="UPDATE002",
            data_source="custom",
            energy_in_kcal_per_100g=0,
            energy_in_kj_per_100g=0,
        )
        payload = {"energy_in_kj_per_100g": 100.0}
        response = authenticated_client.patch(
            f"/api/foods/{food.id}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_200_OK

        food.refresh_from_db()
        # 100 / 4.184 = 23.900... -> rounded to 23.9
        assert food.energy_in_kj_per_100g == 100.0
        assert food.energy_in_kcal_per_100g == 23.9

    def test_error_when_both_kcal_and_kj_provided_update(self, authenticated_client):
        """Test that providing both kcal and kj in PATCH returns 400."""
        food = Food.objects.create(
            name="Both Food Update",
            bls_code="UPDATE003",
            data_source="custom",
            energy_in_kcal_per_100g=0,
            energy_in_kj_per_100g=0,
        )
        payload = {"energy_in_kcal_per_100g": 100.0, "energy_in_kj_per_100g": 418.4}
        response = authenticated_client.patch(
            f"/api/foods/{food.id}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # The ViewSet or Serializer should catch this.
        # In my implementation, the ViewSet catches it first in update().
        assert "Cannot set both" in str(response.data)

    def test_negative_kcal_error(self, authenticated_client):
        """Test that providing negative kcal returns 400."""
        food = Food.objects.create(
            name="Negative Food",
            bls_code="UPDATE004",
            data_source="custom",
            energy_in_kcal_per_100g=0,
            energy_in_kj_per_100g=0,
        )
        payload = {"energy_in_kcal_per_100g": -10.0}
        response = authenticated_client.patch(
            f"/api/foods/{food.id}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Must be 0 or greater" in str(response.data)

    def test_negative_kj_error(self, authenticated_client):
        """Test that providing negative kj returns 400."""
        food = Food.objects.create(
            name="Negative Food Kj",
            bls_code="UPDATE005",
            data_source="custom",
            energy_in_kcal_per_100g=0,
            energy_in_kj_per_100g=0,
        )
        payload = {"energy_in_kj_per_100g": -10.0}
        response = authenticated_client.patch(
            f"/api/foods/{food.id}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Must be 0 or greater" in str(response.data)
