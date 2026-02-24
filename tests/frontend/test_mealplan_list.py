import re
import pytest
from playwright.sync_api import expect
from tests.frontend.factories import MealPlanFactory

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Basic rendering
# ---------------------------------------------------------------------------

def test_mealplan_list_basic(logged_in_page, live_server, test_user):
    MealPlanFactory.create_batch(3)

    logged_in_page.goto(live_server.url + "/")

    expect(logged_in_page.locator("h1")).to_have_text("Meal Plans")
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(3)


# ---------------------------------------------------------------------------
# Live search — wait for DOM to settle instead of a fixed sleep
# ---------------------------------------------------------------------------

def test_mealplan_list_search(logged_in_page, live_server, test_user):
    MealPlanFactory(name="Alpha Plan")
    MealPlanFactory(name="Beta Plan")

    logged_in_page.goto(live_server.url + "/")

    search_input = logged_in_page.locator("#liveSearch")
    search_input.fill("Alpha")

    # Wait for the debounced AJAX call to finish and the DOM to reflect 1 row.
    # Using wait_for_function avoids brittle fixed-time sleeps.
    logged_in_page.wait_for_function(
        "document.querySelectorAll('.meal-plan-row').length === 1"
    )

    rows = logged_in_page.locator(".meal-plan-row")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("Alpha Plan")


def test_mealplan_list_search_no_results(logged_in_page, live_server, test_user):
    MealPlanFactory(name="My Plan")

    logged_in_page.goto(live_server.url + "/")

    logged_in_page.locator("#liveSearch").fill("xyznonexistent")

    logged_in_page.wait_for_function(
        "document.querySelectorAll('.meal-plan-row').length === 0"
    )

    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(0)
    expect(logged_in_page.locator(".no-data")).to_be_visible()


# ---------------------------------------------------------------------------
# Row navigation
# ---------------------------------------------------------------------------

def test_mealplan_list_navigation(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Nav Test Plan")

    logged_in_page.goto(live_server.url + "/")

    logged_in_page.locator(".meal-plan-row").first.click()

    expect(logged_in_page).to_have_url(live_server.url + f"/meal-plan/{plan.id}/")


# ---------------------------------------------------------------------------
# Delete a plan from the list
# ---------------------------------------------------------------------------

def test_mealplan_list_delete_plan(logged_in_page, live_server, test_user):
    MealPlanFactory(name="Plan To Delete")

    logged_in_page.goto(live_server.url + "/")
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(1)

    # Click delete button to open the Vue confirmation modal
    logged_in_page.locator(".delete-btn").first.click()
    # Confirm deletion in the modal
    logged_in_page.locator("[data-testid='confirm-delete-btn']").click()

    # Row should disappear without a full page reload
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(0)


# ---------------------------------------------------------------------------
# Pagination appears when more than 10 plans exist
# ---------------------------------------------------------------------------

def test_mealplan_list_pagination(logged_in_page, live_server, test_user):
    MealPlanFactory.create_batch(12)

    logged_in_page.goto(live_server.url + "/")

    # Only 10 rows visible on first page
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(10)
    # Pagination widget must be rendered
    expect(logged_in_page.locator(".pagination")).to_be_visible()

    # Navigate to page 2
    logged_in_page.locator(".pagination .page-link").last.click()
    logged_in_page.wait_for_load_state("networkidle")

    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(2)


# ---------------------------------------------------------------------------
# Unauthenticated access redirects to login
# ---------------------------------------------------------------------------

def test_unauthenticated_redirect_to_login(page, live_server, db):
    page.goto(live_server.url + "/")
    expect(page).to_have_url(re.compile(r".*/login/.*"))
