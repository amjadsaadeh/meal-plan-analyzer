"""
Tests for model-level constraints not covered by existing API tests.

Covers:
  - Food.bls_code unique constraint
  - Food.__str__
  - MealPlanDay.__str__ and default name
  - MealPlanDay nullable meal_plan FK
  - MealPlanFood unique_together constraint (model level)
  - MealPlanDay soft-delete: hard-deleting a plan cascades to days
"""

import pytest
from django.db import IntegrityError
from meals.models import Food, MealPlan, MealPlanDay, MealPlanFood


def _food(**kwargs):
    defaults = dict(
        bls_code="UNIQUE_001",
        name="Test Food",
        energy_in_kj_per_100g=0.0,
        energy_in_kcal_per_100g=0.0,
    )
    defaults.update(kwargs)
    return Food(**defaults)


@pytest.mark.django_db
class TestFoodModel:
    def test_str_returns_name(self):
        food = Food.objects.create(
            bls_code="F001", name="Banana", energy_in_kj_per_100g=371, energy_in_kcal_per_100g=89
        )
        assert str(food) == "Banana"

    def test_bls_code_unique_constraint(self):
        """Creating two Food records with the same bls_code raises IntegrityError."""
        Food.objects.create(
            bls_code="DUP001", name="First", energy_in_kj_per_100g=0, energy_in_kcal_per_100g=0
        )
        with pytest.raises(IntegrityError):
            Food.objects.create(
                bls_code="DUP001", name="Second", energy_in_kj_per_100g=0, energy_in_kcal_per_100g=0
            )

    def test_nutrient_fields_default_to_zero(self):
        """All optional nutrient FloatFields default to 0.0."""
        food = Food.objects.create(
            bls_code="DEFLT", name="Default Food",
            energy_in_kj_per_100g=100, energy_in_kcal_per_100g=24
        )
        assert food.protein_in_g_per_100g == 0.0
        assert food.fat_in_g_per_100g == 0.0
        assert food.vitd_in_mug_per_100g == 0.0

    def test_ordering_is_by_name(self):
        """Food.Meta.ordering = ['name'] → queryset is alphabetical."""
        Food.objects.create(bls_code="ORD_B", name="Zucchini", energy_in_kj_per_100g=0, energy_in_kcal_per_100g=0)
        Food.objects.create(bls_code="ORD_A", name="Avocado", energy_in_kj_per_100g=0, energy_in_kcal_per_100g=0)
        names = list(Food.objects.filter(bls_code__in=["ORD_A", "ORD_B"]).values_list('name', flat=True))
        assert names == ["Avocado", "Zucchini"]


@pytest.mark.django_db
class TestMealPlanDayModel:
    def test_str_returns_name(self):
        day = MealPlanDay.objects.create(name="Monday")
        assert str(day) == "Monday"

    def test_default_name(self):
        day = MealPlanDay.objects.create()
        assert day.name == "Neuer Tag"

    def test_nullable_meal_plan_fk(self):
        """MealPlanDay can exist without a parent MealPlan."""
        day = MealPlanDay.objects.create(name="Orphan Day", meal_plan=None)
        assert day.meal_plan is None
        assert MealPlanDay.objects.filter(pk=day.pk).exists()

    def test_soft_delete_default_is_false(self):
        day = MealPlanDay.objects.create()
        assert day.removed is False

    def test_cascade_delete_from_plan(self):
        """Deleting a MealPlan cascades to its MealPlanDay records."""
        plan = MealPlan.objects.create(name="Cascade Plan")
        day = MealPlanDay.objects.create(name="D1", meal_plan=plan)
        plan.delete()
        assert not MealPlanDay.objects.filter(pk=day.pk).exists()

    def test_ordering_is_by_creation_date_desc(self):
        """MealPlanDay.Meta.ordering = ['-creation_date'] → newest first."""
        plan = MealPlan.objects.create()
        day1 = MealPlanDay.objects.create(name="First", meal_plan=plan)
        day2 = MealPlanDay.objects.create(name="Second", meal_plan=plan)
        days = list(plan.days.values_list('name', flat=True))
        # Second was created later so it should appear first
        assert days[0] == "Second"
        assert days[1] == "First"


@pytest.mark.django_db
class TestMealPlanFoodModel:
    def _make_food(self, bls):
        return Food.objects.create(
            bls_code=bls, name=f"Food {bls}",
            energy_in_kj_per_100g=0, energy_in_kcal_per_100g=0
        )

    def test_unique_together_enforced_at_db_level(self):
        """IntegrityError on duplicate (meal_plan_day, food, meal_type)."""
        plan = MealPlan.objects.create()
        day = MealPlanDay.objects.create(meal_plan=plan)
        food = self._make_food("UNQ_F1")
        MealPlanFood.objects.create(meal_plan_day=day, food=food, amount_in_g=100, meal_type="breakfast")
        with pytest.raises(IntegrityError):
            MealPlanFood.objects.create(meal_plan_day=day, food=food, amount_in_g=200, meal_type="breakfast")

    def test_same_food_different_meal_type_is_allowed(self):
        plan = MealPlan.objects.create()
        day = MealPlanDay.objects.create(meal_plan=plan)
        food = self._make_food("UNQ_F2")
        MealPlanFood.objects.create(meal_plan_day=day, food=food, amount_in_g=100, meal_type="breakfast")
        mpf2 = MealPlanFood.objects.create(meal_plan_day=day, food=food, amount_in_g=50, meal_type="lunch")
        assert mpf2.pk is not None

    def test_default_meal_type_is_breakfast(self):
        plan = MealPlan.objects.create()
        day = MealPlanDay.objects.create(meal_plan=plan)
        food = self._make_food("UNQ_F3")
        mpf = MealPlanFood.objects.create(meal_plan_day=day, food=food, amount_in_g=100)
        assert mpf.meal_type == "breakfast"
