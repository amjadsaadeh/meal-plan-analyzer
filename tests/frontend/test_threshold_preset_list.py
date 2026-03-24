"""Playwright tests for the threshold preset list page."""

import pytest
from playwright.sync_api import expect
from tests.frontend.factories import ThresholdPresetFactory
from meals.models import ThresholdPreset

pytestmark = pytest.mark.django_db


def _goto_list(page, live_server):
    page.goto(live_server.url + "/threshold-presets/")
    page.wait_for_selector("#threshold-preset-list-app table", timeout=15000)


def test_list_shows_preset_name(logged_in_page, live_server):
    ThresholdPresetFactory(name="Adult Standard")
    _goto_list(logged_in_page, live_server)
    expect(logged_in_page.locator(".preset-name-cell").first).to_contain_text(
        "Adult Standard"
    )


def test_search_filters_presets(logged_in_page, live_server):
    ThresholdPresetFactory(name="Adult Standard")
    ThresholdPresetFactory(name="Child Standard")
    _goto_list(logged_in_page, live_server)
    logged_in_page.fill(".search-bar", "Adult")
    logged_in_page.wait_for_timeout(600)
    expect(logged_in_page.locator(".preset-name-cell")).to_have_count(1)
    expect(logged_in_page.locator(".preset-name-cell").first).to_contain_text(
        "Adult Standard"
    )


def test_search_highlights_match(logged_in_page, live_server):
    ThresholdPresetFactory(name="Adult Standard")
    _goto_list(logged_in_page, live_server)
    logged_in_page.fill(".search-bar", "Adult")
    logged_in_page.wait_for_timeout(600)
    strong = logged_in_page.locator(".preset-name-cell strong")
    expect(strong).to_have_count(1)
    expect(strong).to_contain_text("Adult")


def test_expand_chevron_reveals_more_nutrients(logged_in_page, live_server):
    ThresholdPresetFactory(name="Test Preset")
    _goto_list(logged_in_page, live_server)
    # Expanded content starts collapsed (grid-template-rows: 0fr means height 0)
    expanded = logged_in_page.locator(".expanded-content").first
    assert expanded.evaluate("el => el.clientHeight") == 0
    logged_in_page.locator(".btn-expand-chevron").first.click()
    logged_in_page.wait_for_timeout(400)
    assert expanded.evaluate("el => el.clientHeight") > 0


def test_create_button_navigates_to_editor(logged_in_page, live_server):
    _goto_list(logged_in_page, live_server)
    logged_in_page.click(".btn-create")
    logged_in_page.wait_for_url("**/threshold-presets/*/")
    assert "/threshold-presets/" in logged_in_page.url
    assert logged_in_page.url != live_server.url + "/threshold-presets/"


def test_clicking_name_navigates_to_editor(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="Click Me")
    _goto_list(logged_in_page, live_server)
    logged_in_page.locator(".preset-name-cell").first.click()
    logged_in_page.wait_for_url(f"**/threshold-presets/{preset.id}/")
    assert f"/threshold-presets/{preset.id}/" in logged_in_page.url


def test_empty_state_shown_when_no_presets(logged_in_page, live_server):
    ThresholdPreset.objects.all().delete()
    _goto_list(logged_in_page, live_server)
    expect(logged_in_page.locator(".empty-row")).to_be_visible()
