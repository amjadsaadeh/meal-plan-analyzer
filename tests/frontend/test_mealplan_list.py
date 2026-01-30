import pytest
from playwright.sync_api import expect # TODO use async_api?
from tests.frontend.factories import MealPlanFactory

pytestmark = pytest.mark.django_db

def test_mealplan_list_basic(logged_in_page, live_server, test_user):
    # Create some meal plans
    MealPlanFactory.create_batch(3)
    
    logged_in_page.goto(live_server.url + "/")
    
    # Check if heading is present
    expect(logged_in_page.locator("h1")).to_have_text("Meal Plans")
    
    # Check if table has 3 rows (plus header/empty)
    rows = logged_in_page.locator(".meal-plan-row")
    expect(rows).to_have_count(3)

def test_mealplan_list_search(logged_in_page, live_server, test_user):
    MealPlanFactory(name="Alpha Plan")
    MealPlanFactory(name="Beta Plan")
    
    logged_in_page.goto(live_server.url + "/")
    
    search_input = logged_in_page.locator("#liveSearch")
    search_input.fill("Alpha")
    
    # Wait for search debounce
    logged_in_page.wait_for_timeout(500)
    
    rows = logged_in_page.locator(".meal-plan-row")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("Alpha Plan")

def test_mealplan_list_navigation(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Nav Test Plan")
    
    logged_in_page.goto(live_server.url + "/")
    
    # Click on the row
    logged_in_page.locator(".meal-plan-row").first.click()
    
    # Check if on detail page
    expect(logged_in_page).to_have_url(live_server.url + f"/meal-plan/{plan.id}/")
