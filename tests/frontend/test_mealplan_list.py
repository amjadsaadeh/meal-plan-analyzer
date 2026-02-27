import re
import pytest
from playwright.sync_api import expect
from tests.frontend.factories import MealPlanFactory, MealPlanDayFactory

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Basic rendering
# ---------------------------------------------------------------------------

def test_mealplan_list_basic(logged_in_page, live_server, test_user):
    MealPlanFactory.create_batch(3)

    logged_in_page.goto(live_server.url + "/")

    expect(logged_in_page.locator("h1")).to_have_text("Meal Plans")
    # Vue fetches plans asynchronously; to_have_count retries until satisfied
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(3)


# ---------------------------------------------------------------------------
# Create button
# ---------------------------------------------------------------------------

def test_mealplan_list_create_button(logged_in_page, live_server, test_user):
    logged_in_page.goto(live_server.url + "/")

    btn = logged_in_page.locator(".btn-create")
    expect(btn).to_be_visible()
    expect(btn).to_have_attribute("href", "/meal-plan/new/")


# ---------------------------------------------------------------------------
# Live search — client-side filter with 300 ms debounce
# ---------------------------------------------------------------------------

def test_mealplan_list_search(logged_in_page, live_server, test_user):
    MealPlanFactory(name="Alpha Plan")
    MealPlanFactory(name="Beta Plan")

    logged_in_page.goto(live_server.url + "/")
    # Wait for Vue to finish the initial API load
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(2)

    logged_in_page.locator("#liveSearch").fill("Alpha")

    # wait_for_function polls until the reactive filter settles
    logged_in_page.wait_for_function(
        "document.querySelectorAll('.meal-plan-row').length === 1"
    )

    rows = logged_in_page.locator(".meal-plan-row")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("Alpha Plan")


def test_mealplan_list_search_no_results(logged_in_page, live_server, test_user):
    MealPlanFactory(name="My Plan")

    logged_in_page.goto(live_server.url + "/")
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(1)

    logged_in_page.locator("#liveSearch").fill("xyznonexistent")

    logged_in_page.wait_for_function(
        "document.querySelectorAll('.meal-plan-row').length === 0"
    )

    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(0)
    expect(logged_in_page.locator(".no-data")).to_be_visible()


def test_mealplan_list_search_updates_url(logged_in_page, live_server, test_user):
    MealPlanFactory(name="Alpha Plan")
    MealPlanFactory(name="Beta Plan")

    logged_in_page.goto(live_server.url + "/")
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(2)

    logged_in_page.locator("#liveSearch").fill("Alpha")
    logged_in_page.wait_for_function(
        "document.querySelectorAll('.meal-plan-row').length === 1"
    )

    # URL should be synced via history.pushState
    expect(logged_in_page).to_have_url(re.compile(r".*[?&]search=Alpha.*"))


def test_mealplan_list_url_search_param_restores_filter(logged_in_page, live_server, test_user):
    MealPlanFactory(name="Alpha Plan")
    MealPlanFactory(name="Beta Plan")

    # Navigate directly with a search query in the URL
    logged_in_page.goto(live_server.url + "/?search=Alpha")

    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(1)
    expect(logged_in_page.locator(".meal-plan-row").first).to_contain_text("Alpha Plan")
    # Input should be pre-filled from the URL parameter
    expect(logged_in_page.locator("#liveSearch")).to_have_value("Alpha")


# ---------------------------------------------------------------------------
# Row navigation
# ---------------------------------------------------------------------------

def test_mealplan_list_navigation(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Nav Test Plan")

    logged_in_page.goto(live_server.url + "/")
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(1)

    logged_in_page.locator(".meal-plan-row").first.click()

    expect(logged_in_page).to_have_url(live_server.url + f"/meal-plan/{plan.id}/")


# ---------------------------------------------------------------------------
# Day badges
# ---------------------------------------------------------------------------

def test_mealplan_list_day_badges(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Plan With Days")
    day = MealPlanDayFactory(meal_plan=plan, name="Day 1")

    logged_in_page.goto(live_server.url + "/")
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(1)

    badge = logged_in_page.locator(".energy-badge").first
    expect(badge).to_have_text("Day 1")
    expect(badge).to_have_attribute("href", f"/meal-plan/{plan.id}/#day-{day.id}")


def test_mealplan_list_day_badge_click_does_not_navigate_to_plan(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Plan With Day")
    MealPlanDayFactory(meal_plan=plan, name="Day 1")

    logged_in_page.goto(live_server.url + "/")
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(1)

    # Clicking the badge should NOT trigger the row click handler
    # (stopPropagation is set). The browser navigates to the anchor URL,
    # not to the plan detail page without the hash.
    badge = logged_in_page.locator(".energy-badge").first
    badge.click()

    expect(logged_in_page).not_to_have_url(live_server.url + f"/meal-plan/{plan.id}/")


# ---------------------------------------------------------------------------
# Delete a plan from the list
# ---------------------------------------------------------------------------

def test_mealplan_list_delete_plan(logged_in_page, live_server, test_user):
    MealPlanFactory(name="Plan To Delete")

    logged_in_page.goto(live_server.url + "/")
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(1)

    logged_in_page.locator(".delete-btn").first.click()

    # Custom modal should appear with the plan name
    modal = logged_in_page.locator(".modal-overlay")
    expect(modal).to_be_visible()
    expect(modal.locator(".modal-plan-name")).to_have_text("Plan To Delete")

    # Confirm deletion
    modal.locator(".btn-modal-delete").click()

    # Row should disappear without a full page reload
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(0)


def test_mealplan_list_delete_cancel_keeps_plan(logged_in_page, live_server, test_user):
    MealPlanFactory(name="Plan To Keep")

    logged_in_page.goto(live_server.url + "/")
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(1)

    logged_in_page.locator(".delete-btn").first.click()

    # Custom modal should appear
    modal = logged_in_page.locator(".modal-overlay")
    expect(modal).to_be_visible()

    # Cancel — modal closes, plan stays
    modal.locator(".btn-modal-cancel").click()
    expect(modal).not_to_be_visible()
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(1)


# ---------------------------------------------------------------------------
# Pagination appears when more than 10 plans exist
# ---------------------------------------------------------------------------

def test_mealplan_list_pagination(logged_in_page, live_server, test_user):
    MealPlanFactory.create_batch(12)

    logged_in_page.goto(live_server.url + "/")

    # Only 10 rows visible on first page
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(10)
    expect(logged_in_page.locator(".pagination")).to_be_visible()

    # Navigate to page 2 via the next (>>) button
    logged_in_page.locator(".pagination .page-link").last.click()

    # Client-side navigation — expect auto-retries until count settles
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(2)


# ---------------------------------------------------------------------------
# Unauthenticated access redirects to login
# ---------------------------------------------------------------------------

def test_unauthenticated_redirect_to_login(page, live_server, db):
    page.goto(live_server.url + "/")
    expect(page).to_have_url(re.compile(r".*/login/.*"))
