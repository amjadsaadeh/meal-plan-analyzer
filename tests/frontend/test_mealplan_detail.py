import re
import pytest
from playwright.sync_api import expect
from tests.frontend.factories import (
    MealPlanFactory,
    MealPlanDayFactory,
    FoodFactory,
    MealPlanFoodFactory,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Plan name editing
# ---------------------------------------------------------------------------

def test_mealplan_detail_edit_name(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Original Name")
    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")

    title = logged_in_page.locator("#planName")
    title.click()
    title.fill("Updated Name")

    # Wait for "Unsaved changes" to confirm the JS detected the edit, then
    # wait for "Saved" to confirm the debounced API call succeeded.
    expect(logged_in_page.locator("#syncText")).to_have_text("Unsaved changes", timeout=5000)
    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)

    logged_in_page.reload()
    expect(logged_in_page.locator("#planName")).to_have_text("Updated Name")


# ---------------------------------------------------------------------------
# Adding a day
# ---------------------------------------------------------------------------

def test_mealplan_detail_add_day(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Add Day Test")
    MealPlanDayFactory(meal_plan=plan, name="Tag 1")

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    expect(logged_in_page.locator(".day-section")).to_have_count(1)

    logged_in_page.click("button.col-select-btn:has-text('Add Day')")

    # Page reloads after adding; just verify the count, not the exact new day name
    logged_in_page.wait_for_load_state("networkidle")
    expect(logged_in_page.locator(".day-section")).to_have_count(2)


# ---------------------------------------------------------------------------
# Day deletion
# ---------------------------------------------------------------------------

def test_delete_day(logged_in_page, live_server, test_user):
    plan = MealPlanFactory()
    MealPlanDayFactory(meal_plan=plan, name="Tag Zum Löschen")

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    expect(logged_in_page.locator(".day-section")).to_have_count(1)

    # The delete button has low opacity by default — hover reveals it
    delete_btn = logged_in_page.locator(".day-section .delete-btn").first
    delete_btn.hover()
    delete_btn.click()

    # Confirm modal is shown
    modal = logged_in_page.locator("#deleteDayModal")
    expect(modal).to_have_class(re.compile(r"active"))

    # Confirm deletion
    logged_in_page.locator("#confirmDeleteDayBtn").click()

    # Day section must disappear from the DOM
    expect(logged_in_page.locator(".day-section")).to_have_count(0)


# ---------------------------------------------------------------------------
# Ingredient (MealPlanFood) deletion
# ---------------------------------------------------------------------------

def test_delete_ingredient(logged_in_page, live_server, test_user, meal_plan_with_food):
    plan, day, food, mpf = meal_plan_with_food

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")

    # One real ingredient row must exist
    expect(logged_in_page.locator(".ingredient-row")).to_have_count(1)

    # Accept the confirmation dialog
    logged_in_page.on("dialog", lambda dialog: dialog.accept())
    logged_in_page.locator(".ingredient-row .delete-btn").first.click()

    # Row should be removed from the DOM
    expect(logged_in_page.locator(".ingredient-row")).to_have_count(0)


# ---------------------------------------------------------------------------
# Nutrient calculation — initial render and JS recalculation
# ---------------------------------------------------------------------------

def test_nutrient_calculation_initial_render(logged_in_page, live_server, test_user):
    """Server-rendered values must match food * amount / 100."""
    plan = MealPlanFactory()
    day = MealPlanDayFactory(meal_plan=plan)
    food = FoodFactory(
        name="Calc Food",
        energy_in_kcal_per_100g=200.0,
        protein_in_g_per_100g=20.0,
    )
    MealPlanFoodFactory(meal_plan_day=day, food=food, amount_in_g=150.0, meal_type="breakfast")

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")

    row = logged_in_page.locator(".ingredient-row").first
    # 150g × 200 kcal/100 g = 300.0
    expect(row.locator(".energy_in_kcal-cell")).to_have_text("300.0")
    # 150g × 20 g protein/100 g = 30.0
    expect(row.locator(".protein_in_g-cell")).to_have_text("30.0")


def test_nutrient_calculation_js_recalc(logged_in_page, live_server, test_user):
    """After changing amount in the UI the JS must update nutrient cells."""
    plan = MealPlanFactory()
    day = MealPlanDayFactory(meal_plan=plan)
    food = FoodFactory(
        name="Recalc Food",
        energy_in_kcal_per_100g=100.0,
        protein_in_g_per_100g=10.0,
    )
    MealPlanFoodFactory(meal_plan_day=day, food=food, amount_in_g=100.0, meal_type="breakfast")

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")

    row = logged_in_page.locator(".ingredient-row").first
    amount_input = row.locator(".amount-input")

    # Change amount from 100 g to 250 g
    amount_input.fill("250")
    amount_input.dispatch_event("input")

    # 250g × 100 kcal/100 g = 250.0
    expect(row.locator(".energy_in_kcal-cell")).to_have_text("250.0")
    # 250g × 10 g protein/100 g = 25.0
    expect(row.locator(".protein_in_g-cell")).to_have_text("25.0")

    # Wait for the debounced save to complete
    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)


# ---------------------------------------------------------------------------
# Food search & add
# ---------------------------------------------------------------------------

def test_mealplan_detail_food_search_and_add(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Food Search Test")
    day = MealPlanDayFactory(meal_plan=plan, name="Tag 1")
    food = FoodFactory(name="Super Banana", energy_in_kcal_per_100g=89.0)

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")

    # Click the blank name cell to start searching
    name_cell = logged_in_page.locator(".ingredient-name-cell").first
    name_cell.click()

    search_input = name_cell.locator("input")
    search_input.fill("Super")

    # Wait for the dropdown item to appear before clicking it
    dropdown = logged_in_page.locator("#globalSearchDropdown")
    dropdown_item = dropdown.locator("text=Super Banana")
    expect(dropdown_item).to_be_visible(timeout=5000)
    dropdown_item.click()

    expect(name_cell).to_contain_text("Super Banana")

    # Update amount
    row = name_cell.locator("xpath=./ancestor::tr")
    amount_input = row.locator(".amount-input")
    amount_input.fill("200")
    amount_input.dispatch_event("input")

    # 200g × 89 kcal/100 g = 178.0
    expect(row.locator(".energy_in_kcal-cell")).to_have_text("178.0")

    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)


def test_food_search_no_results(logged_in_page, live_server, test_user):
    plan = MealPlanFactory()
    MealPlanDayFactory(meal_plan=plan)

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")

    name_cell = logged_in_page.locator(".ingredient-name-cell").first
    name_cell.click()

    search_input = name_cell.locator("input")
    search_input.fill("zzznonexistentfood")

    dropdown = logged_in_page.locator("#globalSearchDropdown")
    # The dropdown appears with a "no results" message
    expect(dropdown).to_be_visible(timeout=5000)
    expect(dropdown.locator(".search-item")).to_have_count(1)
    expect(dropdown.locator(".search-item")).not_to_contain_text("zzznonexistentfood")


# ---------------------------------------------------------------------------
# Threshold min/max — persist across reload
# ---------------------------------------------------------------------------

def test_threshold_min_max_persist(logged_in_page, live_server, test_user, meal_plan_with_day):
    plan, day = meal_plan_with_day

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")

    # Use the first protein min threshold input (day summary panel)
    min_input = logged_in_page.locator('.threshold-min[data-nut="protein_in_g"]').first
    min_input.fill("55")
    min_input.dispatch_event("input")  # trigger syncThresholds

    # Wait for debounced save (1 s debounce + network)
    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)

    logged_in_page.reload()

    expect(
        logged_in_page.locator('.threshold-min[data-nut="protein_in_g"]').first
    ).to_have_value("55")


def test_threshold_max_persist(logged_in_page, live_server, test_user, meal_plan_with_day):
    plan, day = meal_plan_with_day

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")

    max_input = logged_in_page.locator('.threshold-max[data-nut="energy_in_kcal"]').first
    max_input.fill("2500")
    max_input.dispatch_event("input")

    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)

    logged_in_page.reload()

    expect(
        logged_in_page.locator('.threshold-max[data-nut="energy_in_kcal"]').first
    ).to_have_value("2500")


# ---------------------------------------------------------------------------
# Column visibility toggle — persists after reload
# ---------------------------------------------------------------------------

def test_column_visibility_toggle(logged_in_page, live_server, test_user, meal_plan_with_day):
    plan, day = meal_plan_with_day

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")

    # Open the column selector dropdown
    logged_in_page.locator("#colSelectBtn").click()
    expect(logged_in_page.locator("#colDropdown")).to_have_class(re.compile(r"active"))

    # Uncheck the protein column
    logged_in_page.locator('input[data-col="protein_in_g"]').click()

    # Column header cells with class col-protein_in_g should now be hidden
    expect(logged_in_page.locator(".col-protein_in_g").first).to_be_hidden()

    # Wait for visibility save to propagate
    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)

    # After reload, protein column must still be hidden (server persists the setting)
    logged_in_page.reload()
    expect(logged_in_page.locator(".col-protein_in_g").first).to_be_hidden()


# ---------------------------------------------------------------------------
# Three meal-type sections are present on the page
# ---------------------------------------------------------------------------

def test_all_three_meal_sections_present(logged_in_page, live_server, test_user):
    plan = MealPlanFactory()
    MealPlanDayFactory(meal_plan=plan)

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")

    # Each day renders Breakfast, Lunch, Dinner sections
    expect(logged_in_page.locator(".meal-section")).to_have_count(3)
    expect(logged_in_page.locator(".meal-section")).to_contain_text(["Breakfast", "Lunch", "Dinner"])


# ---------------------------------------------------------------------------
# PDF preview opens in a popup and renders content
# ---------------------------------------------------------------------------

def test_mealplan_detail_pdf_export_preview(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="PDF Test Plan")
    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")

    with logged_in_page.expect_popup() as popup_info:
        logged_in_page.click("text=Preview")

    preview_page = popup_info.value
    preview_page.wait_for_load_state("networkidle")

    preview_page.wait_for_selector(".preview-frame")
    iframe = preview_page.frame_locator(".preview-frame")

    expect(iframe.locator("h1")).to_contain_text("Analysis: PDF Test Plan")
    expect(iframe.locator("body")).to_contain_text("Average daily intake")
