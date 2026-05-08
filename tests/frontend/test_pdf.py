"""
PDF-related tests split into two layers:
  1. Unit tests — exercise get_meal_plan_context() and WeasyPrint directly (no browser)
  2. Playwright test — verify the preview page renders correct content in the iframe
"""

import pytest
import weasyprint
from django.template.loader import render_to_string
from django.contrib.staticfiles import finders

from tests.frontend.factories import (
    MealPlanFactory,
    MealPlanDayFactory,
    FoodFactory,
    MealPlanFoodFactory,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Unit: get_meal_plan_context() returns correct structure
# ---------------------------------------------------------------------------


def test_get_meal_plan_context_structure():
    """Context dict must contain all required keys with the right types."""
    from meals.views import get_meal_plan_context

    plan = MealPlanFactory(name="Context Test Plan")
    MealPlanDayFactory(meal_plan=plan)

    ctx = get_meal_plan_context(plan.id)

    assert ctx["plan"] == plan
    assert isinstance(ctx["visible_nutrients"], list)
    assert isinstance(ctx["summary_nutrients"], list)
    assert isinstance(ctx["days_data"], list)
    assert ctx["days_count"] >= 1
    # energy_in_kcal is always included regardless of visible_nutrients setting
    keys = [n["key"] for n in ctx["visible_nutrients"]]
    assert "energy_in_kcal" in keys


def test_get_meal_plan_context_nutrient_totals():
    """Nutrient averages must reflect the actual food amounts in the plan."""
    from meals.views import get_meal_plan_context

    plan = MealPlanFactory()
    day = MealPlanDayFactory(meal_plan=plan)
    food = FoodFactory(
        name="Context Nutrient Food",
        energy_in_kcal_per_100g=400.0,
        protein_in_g_per_100g=40.0,
    )
    MealPlanFoodFactory(
        meal_plan_day=day, food=food, amount_in_g=250.0, meal_type="breakfast"
    )

    ctx = get_meal_plan_context(plan.id)

    # With 1 day, the average equals the single day's total
    summary = {n["label"]: n for n in ctx["summary_nutrients"]}

    # Energy (kcal): 250 g × 400 kcal/100 g = 1000 kcal
    assert abs(summary["Energy"]["value"] - 1000.0) < 0.01
    # Protein: 250 g × 40 g/100 g = 100 g
    assert abs(summary["Protein"]["value"] - 100.0) < 0.01


def test_get_meal_plan_context_threshold_status():
    """status must be 'alert' when the average falls clearly outside the defined threshold."""
    from meals.views import get_meal_plan_context
    from meals.models import MealPlan

    plan = MealPlanFactory()
    day = MealPlanDayFactory(meal_plan=plan)
    food = FoodFactory(name="Low Protein Food", protein_in_g_per_100g=1.0)
    MealPlanFoodFactory(
        meal_plan_day=day, food=food, amount_in_g=100.0, meal_type="breakfast"
    )

    # Set a minimum protein threshold of 50 g — the plan has only 1 g (< 95% of 50)
    plan.thresholds = {"protein_in_g": {"min": 50.0, "max": None}}
    plan.save()

    ctx = get_meal_plan_context(plan.id)

    summary = {n["label"]: n for n in ctx["summary_nutrients"]}
    assert summary["Protein"]["status"] == "alert"


# ---------------------------------------------------------------------------
# Unit: WeasyPrint produces a valid (non-empty) PDF binary
# ---------------------------------------------------------------------------


def test_pdf_generation():
    """WeasyPrint must generate a non-empty PDF from the plan context."""
    from meals.views import get_meal_plan_context

    plan = MealPlanFactory(name="WeasyPrint Test Plan")
    MealPlanDayFactory(meal_plan=plan)

    ctx = get_meal_plan_context(plan.id)

    logo_path = finders.find("meals/img/logo.png")
    if logo_path:
        ctx["logo_path"] = f"file://{logo_path}"

    html_string = render_to_string("meals/mealplan_pdf.html.j2", ctx)
    pdf = weasyprint.HTML(
        string=html_string, base_url="http://localhost:8001"
    ).write_pdf()

    assert len(pdf) > 0


def test_pdf_generation_with_food():
    """PDF generation must succeed when the plan contains food items."""
    from meals.views import get_meal_plan_context

    plan = MealPlanFactory(name="PDF With Food")
    day = MealPlanDayFactory(meal_plan=plan)
    food = FoodFactory(name="PDF Banana", energy_in_kcal_per_100g=90.0)
    MealPlanFoodFactory(
        meal_plan_day=day, food=food, amount_in_g=200.0, meal_type="lunch"
    )

    ctx = get_meal_plan_context(plan.id)
    html_string = render_to_string("meals/mealplan_pdf.html.j2", ctx)
    pdf = weasyprint.HTML(
        string=html_string, base_url="http://localhost:8001"
    ).write_pdf()

    assert len(pdf) > 0


# ---------------------------------------------------------------------------
# Unit: minilogo rendering in the PDF template
# ---------------------------------------------------------------------------


def test_minilogo_absent_when_not_in_context():
    """No .day-minilogo element is rendered when minilogo_path is absent from context."""
    from meals.views import get_meal_plan_context

    plan = MealPlanFactory(name="No Minilogo Plan")
    MealPlanDayFactory(meal_plan=plan)

    ctx = get_meal_plan_context(plan.id)
    # minilogo_path intentionally not set
    html = render_to_string("meals/mealplan_pdf.html.j2", ctx)

    assert "day-minilogo" not in html


def test_minilogo_absent_when_none():
    """No .day-minilogo element is rendered when minilogo_path is explicitly None."""
    from meals.views import get_meal_plan_context

    plan = MealPlanFactory(name="Minilogo None Plan")
    MealPlanDayFactory(meal_plan=plan)

    ctx = get_meal_plan_context(plan.id)
    ctx["minilogo_path"] = None
    html = render_to_string("meals/mealplan_pdf.html.j2", ctx)

    assert "day-minilogo" not in html


def test_minilogo_rendered_on_day_pages_not_summary():
    """With minilogo_path set, .day-minilogo appears only in .day-container, not .summary-page."""
    from meals.views import get_meal_plan_context

    plan = MealPlanFactory(name="Minilogo Day Pages Plan")
    MealPlanDayFactory(meal_plan=plan)

    ctx = get_meal_plan_context(plan.id)
    ctx["minilogo_path"] = "http://example.com/minilogo.png"
    html = render_to_string("meals/mealplan_pdf.html.j2", ctx)

    # Locate the summary-page block and check it has no minilogo div
    summary_start = html.index('class="summary-page"')
    day_start = html.index('class="day-container"')
    summary_block = html[summary_start:day_start]
    assert "day-minilogo" not in summary_block

    # The day section must contain at least one minilogo div
    day_section = html[day_start:]
    assert "day-minilogo" in day_section


def test_minilogo_img_src_matches_path():
    """The minilogo img src attribute must equal the provided minilogo_path value."""
    from meals.views import get_meal_plan_context

    plan = MealPlanFactory(name="Minilogo Src Plan")
    MealPlanDayFactory(meal_plan=plan)

    ctx = get_meal_plan_context(plan.id)
    ctx["minilogo_path"] = "/media/logos/mini.png"
    html = render_to_string("meals/mealplan_pdf.html.j2", ctx)

    # Every day-minilogo block must reference the correct src
    assert 'src="/media/logos/mini.png"' in html
    # The src must NOT appear inside the summary-page block
    summary_start = html.index('class="summary-page"')
    day_start = html.index('class="day-container"')
    assert 'src="/media/logos/mini.png"' not in html[summary_start:day_start]


def test_minilogo_count_matches_day_count():
    """One minilogo div must be rendered per day page."""
    from meals.views import get_meal_plan_context

    plan = MealPlanFactory(name="Minilogo Count Plan")
    MealPlanDayFactory(meal_plan=plan)
    MealPlanDayFactory(meal_plan=plan)

    ctx = get_meal_plan_context(plan.id)
    ctx["minilogo_path"] = "http://example.com/minilogo.png"
    html = render_to_string("meals/mealplan_pdf.html.j2", ctx)

    assert html.count('class="day-minilogo"') == 2


def test_pdf_generation_with_minilogo():
    """WeasyPrint must produce a non-empty PDF when minilogo_path is set."""
    from meals.views import get_meal_plan_context

    plan = MealPlanFactory(name="PDF With Minilogo")
    MealPlanDayFactory(meal_plan=plan)

    ctx = get_meal_plan_context(plan.id)
    logo_path = finders.find("meals/img/logo.png")
    if logo_path:
        ctx["logo_path"] = f"file://{logo_path}"
        ctx["minilogo_path"] = f"file://{logo_path}"  # reuse static logo as minilogo

    html_string = render_to_string("meals/mealplan_pdf.html.j2", ctx)
    pdf = weasyprint.HTML(
        string=html_string, base_url="http://localhost:8001"
    ).write_pdf()

    assert len(pdf) > 0


# ---------------------------------------------------------------------------
# Playwright: preview iframe renders the correct plan content
# ---------------------------------------------------------------------------


def test_pdf_preview_iframe_content(logged_in_page, live_server, test_user):
    """The preview iframe must display the plan name and nutrient summary."""
    from playwright.sync_api import expect

    plan = MealPlanFactory(name="Iframe Preview Plan")
    MealPlanDayFactory(meal_plan=plan)

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/preview/")

    logged_in_page.wait_for_selector(".preview-frame")
    iframe = logged_in_page.frame_locator(".preview-frame")

    # The template renders one h1 per section (plan title + each day);
    # use .first to target the plan-level heading specifically.
    expect(iframe.locator("h1").first).to_contain_text("Iframe Preview Plan")
    expect(iframe.locator("body")).to_contain_text("Average daily intake")


def test_default_minilogo_in_preview_without_sitesettings(logged_in_page, live_server):
    """Without a configured minilogo, the default logo is used and .day-minilogo appears in the preview iframe."""
    from playwright.sync_api import expect
    from meals.models import SiteSettings

    # Ensure SiteSettings exists but has no minilogo
    settings = SiteSettings.get()
    assert not settings.minilogo

    plan = MealPlanFactory(name="Default Minilogo Preview")
    MealPlanDayFactory(meal_plan=plan)

    logged_in_page.goto(live_server.url + f"/meal-plan/{plan.id}/preview/")
    logged_in_page.wait_for_selector(".preview-frame")
    iframe = logged_in_page.frame_locator(".preview-frame")

    expect(iframe.locator(".day-minilogo")).to_have_count(1)
