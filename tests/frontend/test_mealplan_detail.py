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


def _wait_for_app(page):
    """Wait until the Vue detail app has fully loaded (toolbar visible)."""
    page.wait_for_selector(".toolbar", timeout=15000)


# ---------------------------------------------------------------------------
# Plan name editing
# ---------------------------------------------------------------------------


def test_mealplan_detail_edit_name(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Original Name")
    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    title = logged_in_page.locator("#planName")
    title.click()
    title.fill("Updated Name")

    # Wait for "Unsaved changes" to confirm Vue detected the edit, then
    # wait for "Saved" to confirm the debounced API call succeeded.
    expect(logged_in_page.locator("#syncText")).to_have_text(
        "Unsaved changes", timeout=5000
    )
    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)

    logged_in_page.reload()
    _wait_for_app(logged_in_page)
    expect(logged_in_page.locator("#planName")).to_have_text("Updated Name")


# ---------------------------------------------------------------------------
# Day name editing
# ---------------------------------------------------------------------------


def test_mealplan_detail_edit_day_name(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Day Name Test")
    MealPlanDayFactory(meal_plan=plan, name="Original Day")

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    day_title = logged_in_page.locator(".editable-day-title").first
    day_title.click()
    day_title.fill("Renamed Day")
    day_title.press("Enter")  # triggers @keydown.enter → blur → onDayNameBlur → save

    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)

    logged_in_page.reload()
    _wait_for_app(logged_in_page)
    expect(logged_in_page.locator(".editable-day-title").first).to_have_text(
        "Renamed Day"
    )


# ---------------------------------------------------------------------------
# Adding a day
# ---------------------------------------------------------------------------


def test_mealplan_detail_add_day(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Add Day Test")
    MealPlanDayFactory(meal_plan=plan, name="Tag 1")

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)
    expect(logged_in_page.locator(".day-section")).to_have_count(1)

    logged_in_page.click("button.col-select-btn:has-text('Add Day')")

    # Vue adds the day reactively — no page reload needed
    expect(logged_in_page.locator(".day-section")).to_have_count(2, timeout=10000)


# ---------------------------------------------------------------------------
# Day deletion
# ---------------------------------------------------------------------------


def test_delete_day(logged_in_page, live_server, test_user):
    plan = MealPlanFactory()
    MealPlanDayFactory(meal_plan=plan, name="Tag Zum Löschen")

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)
    expect(logged_in_page.locator(".day-section")).to_have_count(1)

    # Capture console logs
    logged_in_page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    # The delete button has low opacity by default — hover reveals it
    delete_btn = logged_in_page.locator(".day-title-container .delete-btn").first
    delete_btn.hover()
    delete_btn.click(force=True)

    # Confirm modal is shown (overlay has class="modal-overlay active" when rendered)
    modal = logged_in_page.locator("#deleteDayModal")
    modal.wait_for(state="visible", timeout=10000)
    expect(modal).to_have_class(re.compile(r"active"))

    # Confirm deletion
    logged_in_page.locator("#confirmDeleteDayBtn").click()

    # Day section must disappear from the DOM
    expect(logged_in_page.locator(".day-section")).to_have_count(0, timeout=10000)


# ---------------------------------------------------------------------------
# Ingredient (MealPlanFood) deletion
# ---------------------------------------------------------------------------


def test_delete_ingredient(logged_in_page, live_server, test_user, meal_plan_with_food):
    plan, day, food, mpf = meal_plan_with_food

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    # Only rows with data-id are real (persisted) ingredients; draft rows omit the attribute
    expect(logged_in_page.locator(".ingredient-row[data-id]")).to_have_count(
        1, timeout=10000
    )

    # Trigger the deletion modal
    logged_in_page.locator(".ingredient-row[data-id] .delete-btn").first.click()

    # Wait for the modal and confirm deletion
    modal = logged_in_page.locator("#deleteIngredientModal")
    expect(modal).to_have_class(re.compile(r"active"))
    logged_in_page.locator("#confirmDeleteIngredientBtn").click()

    # Real row should be removed from the DOM
    expect(logged_in_page.locator(".ingredient-row[data-id]")).to_have_count(
        0, timeout=10000
    )


# ---------------------------------------------------------------------------
# Inline delete button (column next to ingredient name)
# ---------------------------------------------------------------------------


def test_inline_delete_button_visible_for_saved_ingredient(
    logged_in_page, live_server, test_user, meal_plan_with_food
):
    """Each saved ingredient row must have two delete buttons (inline + end-of-row)."""
    plan, day, food, mpf = meal_plan_with_food

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    row = logged_in_page.locator(".ingredient-row[data-id]").first
    expect(row).to_be_visible(timeout=10000)
    expect(row.locator(".delete-btn")).to_have_count(2)


def test_inline_delete_button_hidden_for_empty_draft_row(
    logged_in_page, live_server, test_user
):
    """Draft rows with no food selected must show no delete buttons."""
    plan = MealPlanFactory()
    MealPlanDayFactory(meal_plan=plan)

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    # Only draft rows exist — none have a food selected
    draft_rows = logged_in_page.locator(".ingredient-row:not([data-id])")
    expect(draft_rows).to_have_count(3, timeout=10000)
    for i in range(draft_rows.count()):
        expect(draft_rows.nth(i).locator(".delete-btn")).to_have_count(0)



def test_inline_delete_button_triggers_delete_flow(
    logged_in_page, live_server, test_user, meal_plan_with_food
):
    """Clicking the inline (first) delete button opens the same confirmation modal."""
    plan, day, food, mpf = meal_plan_with_food

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    expect(logged_in_page.locator(".ingredient-row[data-id]")).to_have_count(
        1, timeout=10000
    )

    # The inline button is first in DOM order within the row
    row = logged_in_page.locator(".ingredient-row[data-id]").first
    row.locator(".delete-btn").first.click()

    modal = logged_in_page.locator("#deleteIngredientModal")
    expect(modal).to_have_class(re.compile(r"active"))
    logged_in_page.locator("#confirmDeleteIngredientBtn").click()

    expect(logged_in_page.locator(".ingredient-row[data-id]")).to_have_count(
        0, timeout=10000
    )


def test_end_of_row_delete_button_still_works(
    logged_in_page, live_server, test_user, meal_plan_with_food
):
    """Clicking the end-of-row (last) delete button still opens the confirmation modal."""
    plan, day, food, mpf = meal_plan_with_food

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    expect(logged_in_page.locator(".ingredient-row[data-id]")).to_have_count(
        1, timeout=10000
    )

    row = logged_in_page.locator(".ingredient-row[data-id]").first
    row.locator(".delete-btn").last.click()

    modal = logged_in_page.locator("#deleteIngredientModal")
    expect(modal).to_have_class(re.compile(r"active"))
    logged_in_page.locator("#confirmDeleteIngredientBtn").click()

    expect(logged_in_page.locator(".ingredient-row[data-id]")).to_have_count(
        0, timeout=10000
    )


# ---------------------------------------------------------------------------
# Nutrient calculation — initial render and JS recalculation
# ---------------------------------------------------------------------------


def test_nutrient_calculation_initial_render(logged_in_page, live_server, test_user):
    """Vue-computed nutrient values must match food * amount / 100."""
    plan = MealPlanFactory()
    day = MealPlanDayFactory(meal_plan=plan)
    food = FoodFactory(
        name="Calc Food",
        energy_in_kcal_per_100g=200.0,
        protein_in_g_per_100g=20.0,
    )
    MealPlanFoodFactory(
        meal_plan_day=day, food=food, amount_in_g=150.0, meal_type="breakfast"
    )

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    row = logged_in_page.locator(".ingredient-row[data-id]").first
    expect(row).to_be_visible(timeout=10000)

    # 150g × 200 kcal/100 g = 300.0
    expect(row.locator(".energy_in_kcal-cell")).to_have_text("300.0")
    # 150g × 20 g protein/100 g = 30.0
    expect(row.locator(".protein_in_g-cell")).to_have_text("30.0")


def test_nutrient_calculation_js_recalc(logged_in_page, live_server, test_user):
    """After changing amount the Vue computed cells must update reactively."""
    plan = MealPlanFactory()
    day = MealPlanDayFactory(meal_plan=plan)
    food = FoodFactory(
        name="Recalc Food",
        energy_in_kcal_per_100g=100.0,
        protein_in_g_per_100g=10.0,
    )
    MealPlanFoodFactory(
        meal_plan_day=day, food=food, amount_in_g=100.0, meal_type="breakfast"
    )

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    row = logged_in_page.locator(".ingredient-row[data-id]").first
    expect(row).to_be_visible(timeout=10000)
    amount_input = row.locator(".amount-input")

    # Change amount from 100 g to 250 g — @input fires onAmountInput → localAmount updates
    amount_input.fill("250")

    # 250g × 100 kcal/100 g = 250.0 (Vue reactive computed)
    expect(row.locator(".energy_in_kcal-cell")).to_have_text("250.0")
    # 250g × 10 g protein/100 g = 25.0
    expect(row.locator(".protein_in_g-cell")).to_have_text("25.0")

    # Blur triggers onAmountBlur → emitSave → API PATCH
    amount_input.blur()
    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)


# ---------------------------------------------------------------------------
# Meal subtotals (tfoot)
# ---------------------------------------------------------------------------


def test_meal_subtotals_update(logged_in_page, live_server, test_user):
    """The tfoot subtotal row must reflect the computed sum of saved ingredients."""
    plan = MealPlanFactory()
    day = MealPlanDayFactory(meal_plan=plan)
    food = FoodFactory(name="Subtotal Food", energy_in_kcal_per_100g=400.0)
    MealPlanFoodFactory(
        meal_plan_day=day, food=food, amount_in_g=50.0, meal_type="breakfast"
    )

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    expect(logged_in_page.locator(".ingredient-row[data-id]")).to_be_visible(
        timeout=10000
    )

    # 50g × 400 kcal/100 g = 200.0
    breakfast_table = logged_in_page.locator("table[data-meal-type='breakfast']").first
    subtotal_cell = breakfast_table.locator("tfoot .total-value").first
    expect(subtotal_cell).to_have_text("200.0", timeout=5000)


# ---------------------------------------------------------------------------
# Food search & add
# ---------------------------------------------------------------------------


def test_mealplan_detail_food_search_and_add(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="Food Search Test")
    day = MealPlanDayFactory(meal_plan=plan, name="Tag 1")
    food = FoodFactory(name="Super Banana", energy_in_kcal_per_100g=89.0)

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    # Click the blank name cell to start searching (first draft row)
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

    # Update amount — Vue recalculates cells reactively, blur triggers saveRow()
    row = name_cell.locator("xpath=./ancestor::tr")
    amount_input = row.locator(".amount-input")
    amount_input.fill("200")

    # 200g × 89 kcal/100 g = 178.0
    expect(row.locator(".energy_in_kcal-cell")).to_have_text("178.0")

    # Blur to trigger onAmountBlur → emitSave() → API POST
    amount_input.blur()
    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)


def test_food_search_no_results(logged_in_page, live_server, test_user):
    plan = MealPlanFactory()
    MealPlanDayFactory(meal_plan=plan)

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    name_cell = logged_in_page.locator(".ingredient-name-cell").first
    name_cell.click()

    search_input = name_cell.locator("input")
    search_input.fill("zzznonexistentfood")

    dropdown = logged_in_page.locator("#globalSearchDropdown")
    # The no-results dropdown appears with a "no results" message
    expect(dropdown).to_be_visible(timeout=5000)
    expect(dropdown.locator(".search-item")).to_have_count(1)
    expect(dropdown.locator(".search-item")).not_to_contain_text("zzznonexistentfood")


# ---------------------------------------------------------------------------
# Food appears in the correct meal section
# ---------------------------------------------------------------------------


def test_food_in_correct_meal_section(logged_in_page, live_server, test_user):
    """A food added to 'lunch' must only appear in the lunch meal table."""
    plan = MealPlanFactory()
    day = MealPlanDayFactory(meal_plan=plan)
    food = FoodFactory(name="Lunch Item", energy_in_kcal_per_100g=300.0)
    MealPlanFoodFactory(
        meal_plan_day=day, food=food, amount_in_g=100.0, meal_type="lunch"
    )

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    expect(logged_in_page.locator(".ingredient-row[data-id]")).to_be_visible(
        timeout=10000
    )

    # The food must appear in the lunch table
    lunch_table = logged_in_page.locator("table[data-meal-type='lunch']").first
    expect(lunch_table).to_contain_text("Lunch Item")

    # Must not appear in the breakfast table
    breakfast_table = logged_in_page.locator("table[data-meal-type='breakfast']").first
    expect(breakfast_table).not_to_contain_text("Lunch Item")


# ---------------------------------------------------------------------------
# Threshold min/max — persist across reload
# ---------------------------------------------------------------------------


def test_threshold_min_max_persist(
    logged_in_page, live_server, test_user, meal_plan_with_day
):
    plan, day = meal_plan_with_day

    # Side panels are hidden below 1280px; use a desktop viewport to interact with them
    logged_in_page.set_viewport_size({"width": 1440, "height": 900})
    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    # Use the first protein min threshold input (day summary panel)
    min_input = logged_in_page.locator('.threshold-min[data-nut="protein_in_g"]').first
    min_input.fill("55")
    min_input.dispatch_event("input")  # trigger Vue @input handler

    # Wait for debounced save (800ms debounce + network)
    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)

    logged_in_page.reload()
    _wait_for_app(logged_in_page)

    expect(
        logged_in_page.locator('.threshold-min[data-nut="protein_in_g"]').first
    ).to_have_value("55")


def test_threshold_max_persist(
    logged_in_page, live_server, test_user, meal_plan_with_day
):
    plan, day = meal_plan_with_day

    # Side panels are hidden below 1280px; use a desktop viewport to interact with them
    logged_in_page.set_viewport_size({"width": 1440, "height": 900})
    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    max_input = logged_in_page.locator(
        '.threshold-max[data-nut="energy_in_kcal"]'
    ).first
    max_input.fill("2500")
    max_input.dispatch_event("input")

    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)

    logged_in_page.reload()
    _wait_for_app(logged_in_page)

    expect(
        logged_in_page.locator('.threshold-max[data-nut="energy_in_kcal"]').first
    ).to_have_value("2500")


# ---------------------------------------------------------------------------
# Day summary totals
# ---------------------------------------------------------------------------


def test_day_summary_total(logged_in_page, live_server, test_user):
    """The day summary panel must show the correct reactive total for a nutrient."""
    plan = MealPlanFactory()
    day = MealPlanDayFactory(meal_plan=plan)
    food = FoodFactory(name="Summary Food", energy_in_kcal_per_100g=500.0)
    MealPlanFoodFactory(
        meal_plan_day=day, food=food, amount_in_g=200.0, meal_type="breakfast"
    )

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    expect(logged_in_page.locator(".ingredient-row[data-id]")).to_be_visible(
        timeout=10000
    )

    # 200g × 500 kcal/100 g = 1000.0
    energy_val = logged_in_page.locator(
        ".day-summary .col-energy_in_kcal .summary-val"
    ).first
    expect(energy_val).to_have_text("1000.0", timeout=5000)


# ---------------------------------------------------------------------------
# Column visibility toggle — persists after reload
# ---------------------------------------------------------------------------


def test_column_visibility_toggle(
    logged_in_page, live_server, test_user, meal_plan_with_day
):
    plan, day = meal_plan_with_day

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    # Open the column selector dropdown
    logged_in_page.locator("#colSelectBtn").click()
    expect(logged_in_page.locator("#colDropdown")).to_have_class(re.compile(r"active"))

    # Uncheck the protein column
    logged_in_page.locator('#colDropdown input[data-col="protein_in_g"]').click()

    # Column header cells with class col-protein_in_g should now be hidden
    expect(logged_in_page.locator(".col-protein_in_g").first).to_be_hidden()

    # Wait for visibility save to propagate
    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)

    # After reload, protein column must still be hidden (server persists the setting)
    logged_in_page.reload()
    _wait_for_app(logged_in_page)
    expect(logged_in_page.locator(".col-protein_in_g").first).to_be_hidden()


# ---------------------------------------------------------------------------
# Three meal-type sections are present on the page
# ---------------------------------------------------------------------------


def test_all_three_meal_sections_present(logged_in_page, live_server, test_user):
    plan = MealPlanFactory()
    MealPlanDayFactory(meal_plan=plan)

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    # Each day renders Breakfast, Lunch, Dinner sections
    expect(logged_in_page.locator(".meal-section")).to_have_count(3, timeout=10000)
    expect(logged_in_page.locator(".meal-section")).to_contain_text(
        ["Breakfast", "Lunch", "Dinner"]
    )


# ---------------------------------------------------------------------------
# Plan overview section is present
# ---------------------------------------------------------------------------


def test_plan_overview_section_present(logged_in_page, live_server, test_user):
    """The plan overview (daily average) section must be visible below the day sections."""
    plan = MealPlanFactory()
    MealPlanDayFactory(meal_plan=plan)

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    expect(logged_in_page.locator(".meal-summary")).to_be_visible(timeout=10000)


# ---------------------------------------------------------------------------
# Multiple days render independently
# ---------------------------------------------------------------------------


def test_multiple_days_render_independently(logged_in_page, live_server, test_user):
    """Two days must each have their own day-section with the correct data-day-id."""
    plan = MealPlanFactory()
    day1 = MealPlanDayFactory(meal_plan=plan, name="Day One")
    day2 = MealPlanDayFactory(meal_plan=plan, name="Day Two")

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    expect(logged_in_page.locator(".day-section")).to_have_count(2, timeout=10000)
    # Use .day-section to avoid matching the tables that also carry data-day-id
    expect(
        logged_in_page.locator(f'.day-section[data-day-id="{day1.id}"]')
    ).to_be_visible()
    expect(
        logged_in_page.locator(f'.day-section[data-day-id="{day2.id}"]')
    ).to_be_visible()
    expect(
        logged_in_page.locator(f'.day-section[data-day-id="{day1.id}"]')
    ).to_contain_text("Day One")
    expect(
        logged_in_page.locator(f'.day-section[data-day-id="{day2.id}"]')
    ).to_contain_text("Day Two")


# ---------------------------------------------------------------------------
# Sticky bar is present in the DOM
# ---------------------------------------------------------------------------


def test_sticky_bar_in_dom(logged_in_page, live_server, test_user):
    """The sticky bar must be rendered in the DOM and contain the sync status element."""
    plan = MealPlanFactory()
    MealPlanDayFactory(meal_plan=plan)

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    # The sticky bar is always rendered (visibility is CSS-controlled via .visible class)
    expect(logged_in_page.locator("#stickySyncText")).to_be_attached()


# ---------------------------------------------------------------------------
# PDF preview opens in a popup and renders content
# ---------------------------------------------------------------------------


def test_mealplan_detail_pdf_export_preview(logged_in_page, live_server, test_user):
    plan = MealPlanFactory(name="PDF Test Plan")
    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    with logged_in_page.expect_popup() as popup_info:
        logged_in_page.click("text=Export PDF")

    preview_page = popup_info.value
    preview_page.wait_for_load_state("networkidle")

    preview_page.wait_for_selector(".preview-frame")
    iframe = preview_page.frame_locator(".preview-frame")

    expect(iframe.locator("h1")).to_contain_text("Analysis: PDF Test Plan")
    expect(iframe.locator("body")).to_contain_text("Average daily intake")


# ---------------------------------------------------------------------------
# Threshold Presets
# ---------------------------------------------------------------------------


def test_save_threshold_preset(
    logged_in_page, live_server, test_user, meal_plan_with_day
):
    plan, day = meal_plan_with_day
    logged_in_page.set_viewport_size({"width": 1440, "height": 900})
    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    # Fill in some thresholds
    min_input = logged_in_page.locator('.threshold-min[data-nut="protein_in_g"]').first
    min_input.fill("60")
    min_input.dispatch_event("input")
    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)

    # Click "Save reference value template" in the day summary panel
    # (Matches i18n.saveAsTemplate value: "Save as Reference Value Template")
    logged_in_page.locator("text=Save as Reference Value Template").first.click()

    # Wait for modal, fill name and save
    name_input = logged_in_page.locator(".modal-input")
    name_input.fill("My Custom Preset")

    # Wait for validation
    logged_in_page.wait_for_timeout(1000)

    save_btn = logged_in_page.locator(".btn-modal-save")
    expect(save_btn).to_be_enabled()
    save_btn.click()

    # Verify success alert (Playwright handles window.alert automatically or we can check if modal closes)
    expect(logged_in_page.locator(".modal-overlay.active")).to_have_count(
        0, timeout=5000
    )


def test_apply_threshold_preset(
    logged_in_page, live_server, test_user, meal_plan_with_day
):
    plan, day = meal_plan_with_day
    from tests.frontend.factories import ThresholdPresetFactory

    ThresholdPresetFactory(name="Balanced Diet", protein_in_g_min=70.0)

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/")
    _wait_for_app(logged_in_page)

    # Search and apply preset in toolbar
    preset_input = logged_in_page.locator("#presetSearch")
    preset_input.fill("Balanced")

    dropdown_item = logged_in_page.locator(".preset-item:has-text('Balanced Diet')")
    expect(dropdown_item).to_be_visible(timeout=5000)

    # Accept the confirmation dialog
    logged_in_page.on("dialog", lambda dialog: dialog.accept())
    dropdown_item.click()

    # Check if threshold was updated
    expect(logged_in_page.locator("#syncText")).to_have_text("Saved", timeout=10000)

    logged_in_page.set_viewport_size({"width": 1440, "height": 900})
    expect(
        logged_in_page.locator('.threshold-min[data-nut="protein_in_g"]').first
    ).to_have_value("70")
