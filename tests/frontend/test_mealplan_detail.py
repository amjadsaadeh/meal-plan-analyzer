import pytest
from playwright.sync_api import expect
from tests.frontend.factories import MealPlanFactory, FoodFactory, MealPlanDayFactory

pytestmark = pytest.mark.django_db

def test_mealplan_detail_edit_name(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Original Name")
    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    
    # Click on title to edit
    title = logged_in_page.locator("#planName")
    title.click()
    title.fill("Updated Name")
    title.press("Enter")
    
    # Wait for sync
    logged_in_page.wait_for_selector("#syncText:has-text('Saved')")
    
    # Reload and check
    logged_in_page.reload()
    expect(logged_in_page.locator("#planName")).to_have_text("Updated Name")

def test_mealplan_detail_add_day(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Add Day Test")
    MealPlanDayFactory(meal_plan=plan, name="Tag 1")
    
    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    
    expect(logged_in_page.locator(".day-section")).to_have_count(1)
    
    # Click "Tag hinzufügen"
    logged_in_page.click("text=Tag hinzufügen")
    
    # Page reloads after adding day
    logged_in_page.wait_for_load_state("networkidle")
    
    expect(logged_in_page.locator(".day-section")).to_have_count(2)
    # The view orders by -creation_date, so the new day is at the top
    expect(logged_in_page.locator(".day-section").first).to_contain_text("Tag 2")

def test_mealplan_detail_pdf_export_preview(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="PDF Test Plan")
    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    
    # Click "Vorschau" (Preview)
    with logged_in_page.expect_popup() as popup_info:
        logged_in_page.click("text=Vorschau")
    
    preview_page = popup_info.value
    preview_page.wait_for_load_state("networkidle")
    
    preview_page.wait_for_selector(".preview-frame")
    iframe = preview_page.frame_locator(".preview-frame")
    
    # The preview page should contain the plan name inside the iframe
    expect(iframe.locator("h1")).to_contain_text("Auswertung: PDF Test Plan")
    expect(iframe.locator("body")).to_contain_text("Durchschnittliche Aufnahme")

def test_mealplan_detail_food_search_and_add(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Food Search Test")
    day = MealPlanDayFactory(meal_plan=plan, name="Tag 1")
    food = FoodFactory(name="Super Banana", energy_in_kcal_per_100g=89.0)
    
    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    
    # Find the first blank row and its name cell
    # Note: The page automatically adds a blank row for each meal type
    name_cell = logged_in_page.locator(".ingredient-name-cell").first
    name_cell.click()
    
    # An input field should appear inside the cell
    search_input = name_cell.locator("input")
    search_input.fill("Super")
    
    # Wait for dropdown
    dropdown = logged_in_page.locator("#globalSearchDropdown")
    expect(dropdown).to_be_visible()
    
    # Click on the result
    dropdown.locator("text=Super Banana").click()
    
    # The cell should now contain the food name
    expect(name_cell).to_contain_text("Super Banana")
    
    # Update amount
    row = name_cell.locator("xpath=./ancestor::tr")
    amount_input = row.locator(".amount-input")
    amount_input.fill("200")
    amount_input.blur()
    
    # Check if kcal updated (200g * 89kcal/100g = 178)
    expect(row.locator(".energy_in_kcal-cell")).to_have_text("178.0")
    
    # Wait for sync
    logged_in_page.wait_for_selector("#syncText:has-text('Saved')")
