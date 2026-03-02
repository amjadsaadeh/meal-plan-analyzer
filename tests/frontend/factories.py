import factory
from meals.models import Food, MealPlan, MealPlanDay, MealPlanFood, ThresholdPreset

class FoodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Food

    name = factory.Sequence(lambda n: f"Food {n}")
    bls_code = factory.Sequence(lambda n: f"C{n:06d}")
    energy_in_kj_per_100g = 418.0
    energy_in_kcal_per_100g = 100.0
    protein_in_g_per_100g = 10.0
    fat_in_g_per_100g = 5.0
    carbohydrate_in_g_per_100g = 10.0
    fibre_in_g_per_100g = 2.0
    iron_in_mg_per_100g = 1.0
    sugar_in_g_per_100g = 2.0
    omega3_in_g_per_100g = 0.5
    vitc_in_mg_per_100g = 50.0
    magnesium_in_mg_per_100g = 20.0
    zinc_in_mg_per_100g = 1.0
    vitb12_in_mug_per_100g = 0.1
    vita_in_mug_per_100g = 10.0
    calcium_in_mg_per_100g = 30.0
    vitd_in_mug_per_100g = 0.5

class MealPlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MealPlan

    name = factory.Sequence(lambda n: f"Meal Plan {n}")


class MealPlanDayFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MealPlanDay

    meal_plan = factory.SubFactory(MealPlanFactory)
    name = factory.Sequence(lambda n: f"Tag {n+1}")


class MealPlanFoodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MealPlanFood

    meal_plan_day = factory.SubFactory(MealPlanDayFactory)
    food = factory.SubFactory(FoodFactory)
    amount_in_g = 100.0
    meal_type = "breakfast"

class ThresholdPresetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ThresholdPreset

    name = factory.Sequence(lambda n: f"Preset {n}")
