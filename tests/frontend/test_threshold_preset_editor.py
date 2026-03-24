"""Playwright tests for the threshold preset editor page."""

import pytest
from playwright.sync_api import expect
from tests.frontend.factories import ThresholdPresetFactory
from meals.models import ThresholdPreset

pytestmark = pytest.mark.django_db


def _goto_editor(page, live_server, preset):
    page.goto(live_server.url + f"/threshold-presets/{preset.id}/")
    page.wait_for_selector("#threshold-preset-editor-app .preset-header", timeout=15000)


def test_editor_shows_preset_name(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="Adults")
    _goto_editor(logged_in_page, live_server, preset)
    expect(logged_in_page.locator(".preset-name-display")).to_contain_text("Adults")


def test_edit_name_via_pencil_icon(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="Old Name")
    _goto_editor(logged_in_page, live_server, preset)
    logged_in_page.click(".btn-edit-name")
    logged_in_page.fill(".name-input", "New Name")
    logged_in_page.locator(".name-input").blur()
    logged_in_page.wait_for_timeout(600)
    updated = ThresholdPreset.objects.get(pk=preset.id)
    assert updated.name == "New Name"


def test_autosave_indicator_shows_saved_after_blur(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="Test")
    _goto_editor(logged_in_page, live_server, preset)
    logged_in_page.locator(".nutrient-min-input").first.fill("1800")
    logged_in_page.locator(".nutrient-min-input").first.blur()
    expect(logged_in_page.locator(".autosave-indicator")).to_contain_text("Saved")


def test_nutrient_value_persisted_after_blur(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="Test", energy_in_kcal_min=None)
    _goto_editor(logged_in_page, live_server, preset)
    logged_in_page.locator(".nutrient-min-input").first.fill("2000")
    logged_in_page.locator(".nutrient-min-input").first.blur()
    logged_in_page.wait_for_timeout(600)
    updated = ThresholdPreset.objects.get(pk=preset.id)
    assert updated.energy_in_kcal_min == 2000.0


def test_all_nutrients_visible_from_start(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="Test")
    _goto_editor(logged_in_page, live_server, preset)
    rows = logged_in_page.locator(".nutrient-row")
    assert rows.count() == 26


def test_delete_preset_redirects_to_list(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="ToDelete")
    _goto_editor(logged_in_page, live_server, preset)
    logged_in_page.on("dialog", lambda d: d.accept())
    logged_in_page.click(".btn-danger")
    logged_in_page.wait_for_url("**/threshold-presets/")
    assert not ThresholdPreset.objects.filter(pk=preset.id).exists()


def test_back_link_returns_to_list(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="Test")
    _goto_editor(logged_in_page, live_server, preset)
    logged_in_page.click(".back-link")
    expect(logged_in_page).to_have_url(live_server.url + "/threshold-presets/")
