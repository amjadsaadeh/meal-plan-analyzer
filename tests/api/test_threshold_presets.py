"""
Tests for the /api/threshold-presets/ endpoint (ThresholdPresetViewSet).

Covers:
  - Authentication guard on all endpoints
  - Full CRUD: create, list, retrieve, update, delete
  - Unique name constraint enforcement
  - Partial update (PATCH) of individual min/max fields
  - __str__ representation
"""

import pytest
from rest_framework import status
from meals.models import ThresholdPreset


@pytest.mark.django_db
class TestThresholdPresetAuth:
    """Unauthenticated requests are rejected."""

    def test_list_unauthenticated(self, api_client):
        response = api_client.get('/api/threshold-presets/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_unauthenticated(self, api_client):
        response = api_client.post('/api/threshold-presets/', {"name": "Adult"}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestThresholdPresetCRUD:
    """Full CRUD operations for authenticated users."""

    def test_create_minimal(self, authenticated_client):
        """Creating a preset with just a name (all nutrients null) succeeds."""
        response = authenticated_client.post(
            '/api/threshold-presets/', {"name": "Adult"}, format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert ThresholdPreset.objects.filter(name="Adult").exists()

    def test_create_with_nutrient_values(self, authenticated_client):
        """Creating a preset with specific min/max values stores them correctly."""
        payload = {
            "name": "Sporty",
            "energy_in_kcal_min": 2500.0,
            "energy_in_kcal_max": 3500.0,
            "protein_in_g_min": 80.0,
            "protein_in_g_max": 150.0,
        }
        response = authenticated_client.post('/api/threshold-presets/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        preset = ThresholdPreset.objects.get(name="Sporty")
        assert preset.energy_in_kcal_min == 2500.0
        assert preset.protein_in_g_max == 150.0

    def test_list_returns_all_presets(self, authenticated_client):
        """Listing returns all created presets."""
        ThresholdPreset.objects.create(name="A")
        ThresholdPreset.objects.create(name="B")
        response = authenticated_client.get('/api/threshold-presets/')
        assert response.status_code == status.HTTP_200_OK
        names = [p['name'] for p in response.data['results']]
        assert "A" in names
        assert "B" in names

    def test_retrieve_single_preset(self, authenticated_client):
        """Retrieving a single preset by ID returns correct data."""
        preset = ThresholdPreset.objects.create(
            name="Child", energy_in_kcal_min=1200.0, energy_in_kcal_max=1800.0
        )
        response = authenticated_client.get(f'/api/threshold-presets/{preset.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == "Child"
        assert response.data['energy_in_kcal_min'] == 1200.0
        assert response.data['energy_in_kcal_max'] == 1800.0

    def test_update_preset_put(self, authenticated_client):
        """PUT update replaces the preset's name and fields."""
        preset = ThresholdPreset.objects.create(name="Old Name")
        payload = {"name": "New Name", "protein_in_g_min": 60.0}
        response = authenticated_client.put(
            f'/api/threshold-presets/{preset.id}/', payload, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        preset.refresh_from_db()
        assert preset.name == "New Name"
        assert preset.protein_in_g_min == 60.0

    def test_partial_update_preset_patch(self, authenticated_client):
        """PATCH update changes only the supplied fields."""
        preset = ThresholdPreset.objects.create(
            name="Base", energy_in_kcal_min=1800.0, energy_in_kcal_max=2400.0
        )
        response = authenticated_client.patch(
            f'/api/threshold-presets/{preset.id}/',
            {"energy_in_kcal_max": 2800.0},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        preset.refresh_from_db()
        assert preset.energy_in_kcal_min == 1800.0  # unchanged
        assert preset.energy_in_kcal_max == 2800.0  # updated

    def test_delete_preset(self, authenticated_client):
        """DELETE removes the preset from the database."""
        preset = ThresholdPreset.objects.create(name="ToDelete")
        response = authenticated_client.delete(f'/api/threshold-presets/{preset.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ThresholdPreset.objects.filter(pk=preset.id).exists()

    def test_null_nutrient_fields_stored_correctly(self, authenticated_client):
        """Fields not supplied default to null and are returned as null."""
        response = authenticated_client.post(
            '/api/threshold-presets/', {"name": "Sparse"}, format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['energy_in_kcal_min'] is None
        assert response.data['vitd_in_mug_max'] is None


@pytest.mark.django_db
class TestThresholdPresetConstraints:
    """Model-level constraint tests."""

    def test_duplicate_name_rejected(self, authenticated_client):
        """Creating two presets with the same name returns 400."""
        ThresholdPreset.objects.create(name="Unique")
        response = authenticated_client.post(
            '/api/threshold-presets/', {"name": "Unique"}, format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_str_returns_name(self):
        """__str__ returns the preset name."""
        preset = ThresholdPreset(name="My Preset")
        assert str(preset) == "My Preset"
