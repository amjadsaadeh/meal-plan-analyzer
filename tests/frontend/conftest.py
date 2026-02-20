import os
import pytest
from django.contrib.auth.models import User
from playwright.sync_api import Page, expect
from tests.frontend.factories import (
    MealPlanFactory,
    MealPlanDayFactory,
    FoodFactory,
    MealPlanFoodFactory,
)

# Set this at module level to be sure it's active before any Django code runs in this process
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


@pytest.fixture
def test_password():
    return "pass1234"


@pytest.fixture
def test_user(db, test_password):
    return User.objects.create_user(username="testadmin", password=test_password)


@pytest.fixture
def logged_in_page(page: Page, live_server, test_user, test_password):
    page.goto(live_server.url + "/login/")
    page.fill("#id_username", test_user.username)
    page.fill("#id_password", test_password)
    page.click(".btn-login")

    # Verify login success by checking for a logout button or redirect to meal plans
    expect(page).to_have_url(live_server.url + "/")
    return page


@pytest.fixture
def meal_plan_with_day(db):
    """Returns (plan, day) — a plan with a single active day."""
    plan = MealPlanFactory()
    day = MealPlanDayFactory(meal_plan=plan)
    return plan, day


@pytest.fixture
def meal_plan_with_food(db):
    """Returns (plan, day, food, mpf) — a plan with a day that has one breakfast ingredient."""
    plan = MealPlanFactory()
    day = MealPlanDayFactory(meal_plan=plan)
    food = FoodFactory(
        name="Test Ingredient",
        energy_in_kcal_per_100g=200.0,
        protein_in_g_per_100g=20.0,
        fat_in_g_per_100g=10.0,
        carbohydrate_in_g_per_100g=25.0,
    )
    mpf = MealPlanFoodFactory(meal_plan_day=day, food=food, amount_in_g=100.0, meal_type="breakfast")
    return plan, day, food, mpf
