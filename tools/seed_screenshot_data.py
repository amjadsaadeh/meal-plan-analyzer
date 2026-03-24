import os
import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from meals.models import MealPlan, MealPlanDay, MealPlanFood, Food, ThresholdPreset

User = get_user_model()
user, _ = User.objects.get_or_create(
    username="testuser", defaults={"email": "test@example.com"}
)
user.set_password("Test1234")
user.save()

# Create a rich meal plan
plan = MealPlan.objects.create(name="Weekly Balanced Plan")

# Add Day 1
day1 = MealPlanDay.objects.create(meal_plan=plan, name="Monday")


# We have 7142 foods. Let's find some standard foods by their names
def get_food(query):
    return Food.objects.filter(name__icontains=query).first()


food_oats = get_food("Hafer")
if not food_oats:
    food_oats = Food.objects.first()

food_milk = get_food("Milch")
if not food_milk:
    food_milk = Food.objects.first()

food_chicken = get_food("Hähnchen")
if not food_chicken:
    food_chicken = Food.objects.first()

food_rice = get_food("Reis")
if not food_rice:
    food_rice = Food.objects.first()

food_apple = get_food("Apfel")
if not food_apple:
    food_apple = Food.objects.first()

food_pasta = get_food("Nudeln")
if not food_pasta:
    food_pasta = Food.objects.first()

food_tomato = get_food("Tomate")
if not food_tomato:
    food_tomato = Food.objects.first()

# Breakfast
MealPlanFood.objects.create(
    meal_plan_day=day1,
    food=food_oats,
    amount_in_g=80,
    meal_type="breakfast",
    export_name="Oats",
)
MealPlanFood.objects.create(
    meal_plan_day=day1,
    food=food_milk,
    amount_in_g=200,
    meal_type="breakfast",
    export_name="Milk",
)
MealPlanFood.objects.create(
    meal_plan_day=day1,
    food=food_apple,
    amount_in_g=150,
    meal_type="breakfast",
    export_name="Apple",
)

# Lunch
MealPlanFood.objects.create(
    meal_plan_day=day1,
    food=food_chicken,
    amount_in_g=200,
    meal_type="lunch",
    export_name="Chicken",
)
MealPlanFood.objects.create(
    meal_plan_day=day1,
    food=food_rice,
    amount_in_g=100,
    meal_type="lunch",
    export_name="Rice",
)

# Dinner
MealPlanFood.objects.create(
    meal_plan_day=day1,
    food=food_pasta,
    amount_in_g=120,
    meal_type="dinner",
    export_name="Pasta",
)
MealPlanFood.objects.create(
    meal_plan_day=day1,
    food=food_tomato,
    amount_in_g=150,
    meal_type="dinner",
    export_name="Tomato Sauce",
)


# Day 2
day2 = MealPlanDay.objects.create(meal_plan=plan, name="Tuesday")
MealPlanFood.objects.create(
    meal_plan_day=day2,
    food=food_oats,
    amount_in_g=60,
    meal_type="breakfast",
    export_name="Oats",
)
MealPlanFood.objects.create(
    meal_plan_day=day2,
    food=food_milk,
    amount_in_g=150,
    meal_type="breakfast",
    export_name="Milk",
)

# Create thresholds
plan.thresholds = {
    "energy_in_kcal": {"min": 2000, "max": 2500},
    "protein_in_g": {"min": 150, "max": 200},
    "fat_in_g": {"min": 50, "max": 80},
    "carbohydrate_in_g": {"min": 250, "max": 300},
}
plan.save()

# Another plan
MealPlan.objects.create(name="Low Carb Trial (Archive)")

print(plan.id)
