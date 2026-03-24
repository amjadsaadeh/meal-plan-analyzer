"""
Take screenshots of the meal-plan-analyzer app for the docs landing page.
Dynamically finds the best plan to screenshot.
"""

import os
import sys

# Set up Django so we can query the DB
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from meals.models import MealPlan, MealPlanDay, MealPlanFood

# Find the plan with the most food entries (most visually interesting)
best_plan = None
best_count = 0
for plan in MealPlan.objects.all():
    count = MealPlanFood.objects.filter(meal_plan_day__meal_plan=plan).count()
    print(f"Plan {plan.id} ({plan.name}): {count} foods")
    if count > best_count:
        best_count = count
        best_plan = plan

if not best_plan:
    print("No plans found!")
    sys.exit(1)

print(f"\nUsing plan {best_plan.id}: {best_plan.name} ({best_count} foods)")

from playwright.sync_api import sync_playwright


def run(plan_id):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Login
        print("Logging in...")
        page.goto("http://localhost:8000/login/")
        page.wait_for_load_state("networkidle")
        page.fill('input[name="username"]', "testuser")
        page.fill('input[name="password"]', "Test1234")
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_url("http://localhost:8000/")
        page.wait_for_load_state("networkidle")
        print("Logged in OK")

        # 1. Dashboard
        print("Dashboard screenshot...")
        page.goto("http://localhost:8000/")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path="docs/assets/dashboard.png")
        print("  -> saved dashboard.png")

        # 2. Meal Plan Edit
        print(f"Meal Plan Edit screenshot (plan {plan_id})...")
        page.goto(f"http://localhost:8000/meal-plan/{plan_id}/")
        page.wait_for_load_state("domcontentloaded")
        # Wait for Vue to mount - poll until the food table or a known element appears
        for i in range(20):
            page.wait_for_timeout(1000)
            # Check if something meaningful has rendered
            content = page.inner_text("body")
            if (
                "Monday" in content
                or "Tuesday" in content
                or "Breakfast" in content
                or "breakfast" in content.lower()
            ):
                print(f"  Vue loaded after {i+1}s")
                break
        page.wait_for_timeout(1000)  # A little extra settle time
        page.screenshot(path="docs/assets/meal_plan_edit.png")
        print("  -> saved meal_plan_edit.png")

        # 3. PDF Preview
        print(f"PDF Preview screenshot (plan {plan_id})...")
        page.goto(f"http://localhost:8000/meal-plan/{plan_id}/preview/")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        page.screenshot(path="docs/assets/meal_plan_preview.png")
        print("  -> saved meal_plan_preview.png")

        browser.close()
        print("Done!")


run(best_plan.id)
