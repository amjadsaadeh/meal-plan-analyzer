"""Tests for the threshold preset list and editor Django views."""

import pytest
from django.urls import reverse
from meals.models import ThresholdPreset

pytestmark = pytest.mark.django_db


def test_list_redirects_unauthenticated(api_client):
    response = api_client.get("/threshold-presets/")
    assert response.status_code == 302
    assert "login" in response.url


def test_list_renders_ok(authenticated_client):
    response = authenticated_client.get("/threshold-presets/")
    assert response.status_code == 200


def test_list_has_mount_element(authenticated_client):
    response = authenticated_client.get("/threshold-presets/")
    assert b'id="threshold-preset-list-app"' in response.content


def test_list_passes_nutrients_json(authenticated_client):
    response = authenticated_client.get("/threshold-presets/")
    assert b"energy_in_kcal" in response.content


def test_editor_redirects_unauthenticated(api_client):
    preset = ThresholdPreset.objects.create(name="Test")
    response = api_client.get(f"/threshold-presets/{preset.id}/")
    assert response.status_code == 302
    assert "login" in response.url


def test_editor_renders_ok(authenticated_client):
    preset = ThresholdPreset.objects.create(name="Test")
    response = authenticated_client.get(f"/threshold-presets/{preset.id}/")
    assert response.status_code == 200


def test_editor_returns_404_for_missing(authenticated_client):
    response = authenticated_client.get("/threshold-presets/9999/")
    assert response.status_code == 404


def test_editor_has_mount_element(authenticated_client):
    preset = ThresholdPreset.objects.create(name="Test")
    response = authenticated_client.get(f"/threshold-presets/{preset.id}/")
    assert b'id="threshold-preset-editor-app"' in response.content


def test_editor_passes_preset_id(authenticated_client):
    preset = ThresholdPreset.objects.create(name="Test")
    response = authenticated_client.get(f"/threshold-presets/{preset.id}/")
    assert str(preset.id).encode() in response.content


def test_nav_link_present(authenticated_client):
    response = authenticated_client.get("/threshold-presets/")
    assert b"/threshold-presets/" in response.content
