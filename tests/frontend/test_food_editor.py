"""Playwright tests for the food editor aliases section."""
import pytest
from playwright.sync_api import expect
from meals.models import FoodAlias
from tests.frontend.factories import FoodFactory

pytestmark = pytest.mark.django_db


def _goto_editor(page, live_server, food):
    page.goto(live_server.url + f"/foods/{food.id}/")
    # Wait until the aliases section heading is visible
    page.wait_for_selector(".aliases-section", timeout=15000)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_aliases_section_visible_for_bls_food(logged_in_page, live_server):
    food = FoodFactory(data_source="")
    _goto_editor(logged_in_page, live_server, food)
    expect(logged_in_page.locator(".aliases-section")).to_be_visible()


def test_aliases_section_visible_for_custom_food(logged_in_page, live_server):
    food = FoodFactory(data_source="custom")
    _goto_editor(logged_in_page, live_server, food)
    expect(logged_in_page.locator(".aliases-section")).to_be_visible()


def test_empty_state_shows_dash(logged_in_page, live_server):
    food = FoodFactory()
    _goto_editor(logged_in_page, live_server, food)
    expect(logged_in_page.locator(".alias-empty")).to_be_visible()
    expect(logged_in_page.locator(".alias-empty")).to_have_text("—")


def test_existing_alias_shown_as_badge(logged_in_page, live_server):
    food = FoodFactory()
    FoodAlias.objects.create(food=food, alias="Tomato")
    _goto_editor(logged_in_page, live_server, food)
    badge = logged_in_page.locator(".alias-badge").filter(has_text="Tomato")
    expect(badge).to_be_visible()


def test_multiple_existing_aliases_shown(logged_in_page, live_server):
    food = FoodFactory()
    FoodAlias.objects.create(food=food, alias="Alpha")
    FoodAlias.objects.create(food=food, alias="Beta")
    _goto_editor(logged_in_page, live_server, food)
    expect(logged_in_page.locator(".alias-badge")).to_have_count(2)


# ---------------------------------------------------------------------------
# Adding aliases
# ---------------------------------------------------------------------------


def test_add_alias_via_button(logged_in_page, live_server):
    food = FoodFactory()
    _goto_editor(logged_in_page, live_server, food)

    logged_in_page.fill(".alias-input", "Aubergine")
    logged_in_page.click(".alias-add-btn")

    expect(logged_in_page.locator(".alias-badge").filter(has_text="Aubergine")).to_be_visible(
        timeout=8000
    )
    expect(logged_in_page.locator(".alias-input")).to_have_value("")
    assert FoodAlias.objects.filter(food=food, alias="Aubergine").exists()


def test_add_alias_via_enter_key(logged_in_page, live_server):
    food = FoodFactory()
    _goto_editor(logged_in_page, live_server, food)

    logged_in_page.fill(".alias-input", "Zucchini")
    logged_in_page.press(".alias-input", "Enter")

    expect(logged_in_page.locator(".alias-badge").filter(has_text="Zucchini")).to_be_visible(
        timeout=8000
    )
    assert FoodAlias.objects.filter(food=food, alias="Zucchini").exists()


def test_add_button_disabled_when_input_empty(logged_in_page, live_server):
    food = FoodFactory()
    _goto_editor(logged_in_page, live_server, food)
    expect(logged_in_page.locator(".alias-add-btn")).to_be_disabled()


def test_add_button_enabled_when_input_has_text(logged_in_page, live_server):
    food = FoodFactory()
    _goto_editor(logged_in_page, live_server, food)
    logged_in_page.fill(".alias-input", "Something")
    expect(logged_in_page.locator(".alias-add-btn")).to_be_enabled()


def test_add_duplicate_alias_does_not_create_double_badge(logged_in_page, live_server):
    food = FoodFactory()
    FoodAlias.objects.create(food=food, alias="Duplicate")
    _goto_editor(logged_in_page, live_server, food)

    logged_in_page.fill(".alias-input", "Duplicate")
    logged_in_page.click(".alias-add-btn")

    # Still only one badge (backend returns existing object)
    expect(logged_in_page.locator(".alias-badge").filter(has_text="Duplicate")).to_have_count(
        1, timeout=8000
    )


# ---------------------------------------------------------------------------
# Removing aliases
# ---------------------------------------------------------------------------


def test_remove_alias_removes_badge(logged_in_page, live_server):
    food = FoodFactory()
    FoodAlias.objects.create(food=food, alias="RemoveMe")
    _goto_editor(logged_in_page, live_server, food)

    badge = logged_in_page.locator(".alias-badge").filter(has_text="RemoveMe")
    expect(badge).to_be_visible()

    # Accept the confirm dialog automatically
    logged_in_page.on("dialog", lambda dialog: dialog.accept())
    badge.locator(".alias-remove-btn").click()

    expect(logged_in_page.locator(".alias-badge").filter(has_text="RemoveMe")).to_have_count(
        0, timeout=8000
    )
    assert not FoodAlias.objects.filter(food=food, alias="RemoveMe").exists()


def test_remove_alias_cancelled_keeps_badge(logged_in_page, live_server):
    food = FoodFactory()
    FoodAlias.objects.create(food=food, alias="KeepMe")
    _goto_editor(logged_in_page, live_server, food)

    badge = logged_in_page.locator(".alias-badge").filter(has_text="KeepMe")
    expect(badge).to_be_visible()

    # Dismiss the confirm dialog
    logged_in_page.on("dialog", lambda dialog: dialog.dismiss())
    badge.locator(".alias-remove-btn").click()

    # Badge should still be visible
    expect(badge).to_be_visible(timeout=3000)
    assert FoodAlias.objects.filter(food=food, alias="KeepMe").exists()


def test_remove_last_alias_shows_empty_state(logged_in_page, live_server):
    food = FoodFactory()
    FoodAlias.objects.create(food=food, alias="Solo")
    _goto_editor(logged_in_page, live_server, food)

    logged_in_page.on("dialog", lambda dialog: dialog.accept())
    logged_in_page.locator(".alias-badge").filter(has_text="Solo").locator(
        ".alias-remove-btn"
    ).click()

    expect(logged_in_page.locator(".alias-empty")).to_be_visible(timeout=8000)
