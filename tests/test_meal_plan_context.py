"""
Tests for the get_meal_plan_context() helper in meals/views.py.

This function is the core of the PDF/preview feature.  It:
  - calculates per-item nutrient values using amount_in_g / 100 factor
  - sums daily totals and averages across days
  - applies threshold min/max logic (is_ok flag, percentage, ref_val)
  - coerces empty-string thresholds to None
  - respects the plan's visible_nutrients list
  - handles plans with no days or days with no foods gracefully
"""

import pytest
from django.utils import translation
from meals.models import Food, MealPlan, MealPlanDay, MealPlanFood
from meals.views import get_meal_plan_context


@pytest.fixture(autouse=True)
def set_german_locale():
    translation.activate("de")
    yield
    translation.deactivate()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_food(**kwargs):
    """Create a Food with all nutrient fields defaulting to 0."""
    defaults = dict(
        bls_code=f"TEST_{make_food._counter}",
        name=f"Test Food {make_food._counter}",
        energy_in_kj_per_100g=0.0,
        energy_in_kcal_per_100g=0.0,
        protein_in_g_per_100g=0.0,
        fat_in_g_per_100g=0.0,
        carbohydrate_in_g_per_100g=0.0,
        fibre_in_g_per_100g=0.0,
        iron_in_mg_per_100g=0.0,
        sugar_in_g_per_100g=0.0,
        omega3_in_g_per_100g=0.0,
        vitc_in_mg_per_100g=0.0,
        magnesium_in_mg_per_100g=0.0,
        zinc_in_mg_per_100g=0.0,
        vitb12_in_mug_per_100g=0.0,
        vita_in_mug_per_100g=0.0,
        calcium_in_mg_per_100g=0.0,
        vitd_in_mug_per_100g=0.0,
    )
    defaults.update(kwargs)
    make_food._counter += 1
    return Food.objects.create(**defaults)


make_food._counter = 0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetMealPlanContextNutrientCalculation:
    """Nutrient value calculation tests (factor = amount_in_g / 100)."""

    def test_single_food_full_100g(self):
        """100 g of food with 200 kcal/100g → 200 kcal in summary."""
        food = make_food(energy_in_kcal_per_100g=200.0)
        plan = MealPlan.objects.create(
            name="P",
            visible_nutrients=["energy_in_kcal"],
            thresholds={},
        )
        day = MealPlanDay.objects.create(name="D1", meal_plan=plan)
        MealPlanFood.objects.create(
            meal_plan_day=day, food=food, amount_in_g=100.0, meal_type="breakfast"
        )

        ctx = get_meal_plan_context(plan.pk)

        kcal_summary = next(
            n for n in ctx["summary_nutrients"] if n["label"] == "Energie"
        )
        assert kcal_summary["value"] == pytest.approx(200.0)

    def test_single_food_half_portion(self):
        """50 g of food with 400 kcal/100g → 200 kcal."""
        food = make_food(energy_in_kcal_per_100g=400.0)
        plan = MealPlan.objects.create(
            name="P",
            visible_nutrients=["energy_in_kcal"],
            thresholds={},
        )
        day = MealPlanDay.objects.create(name="D1", meal_plan=plan)
        MealPlanFood.objects.create(
            meal_plan_day=day, food=food, amount_in_g=50.0, meal_type="breakfast"
        )

        ctx = get_meal_plan_context(plan.pk)

        kcal_summary = next(
            n for n in ctx["summary_nutrients"] if n["label"] == "Energie"
        )
        assert kcal_summary["value"] == pytest.approx(200.0)

    def test_two_foods_same_day_summed(self):
        """Two foods in one day: their kcal contributions are summed."""
        food1 = make_food(energy_in_kcal_per_100g=100.0)
        food2 = make_food(energy_in_kcal_per_100g=200.0)
        plan = MealPlan.objects.create(
            name="P",
            visible_nutrients=["energy_in_kcal"],
            thresholds={},
        )
        day = MealPlanDay.objects.create(name="D1", meal_plan=plan)
        MealPlanFood.objects.create(
            meal_plan_day=day, food=food1, amount_in_g=100.0, meal_type="breakfast"
        )
        MealPlanFood.objects.create(
            meal_plan_day=day, food=food2, amount_in_g=100.0, meal_type="lunch"
        )

        ctx = get_meal_plan_context(plan.pk)

        kcal_summary = next(
            n for n in ctx["summary_nutrients"] if n["label"] == "Energie"
        )
        assert kcal_summary["value"] == pytest.approx(300.0)

    def test_two_days_average_is_computed(self):
        """Two days with different totals: the summary value is the average."""
        food = make_food(energy_in_kcal_per_100g=100.0)
        plan = MealPlan.objects.create(
            name="P",
            visible_nutrients=["energy_in_kcal"],
            thresholds={},
        )
        day1 = MealPlanDay.objects.create(name="D1", meal_plan=plan)
        day2 = MealPlanDay.objects.create(name="D2", meal_plan=plan)
        # day1: 100g → 100 kcal, day2: 300g → 300 kcal → avg = 200
        MealPlanFood.objects.create(
            meal_plan_day=day1, food=food, amount_in_g=100.0, meal_type="breakfast"
        )
        MealPlanFood.objects.create(
            meal_plan_day=day2, food=food, amount_in_g=300.0, meal_type="breakfast"
        )

        ctx = get_meal_plan_context(plan.pk)

        assert ctx["days_count"] == 2
        kcal_summary = next(
            n for n in ctx["summary_nutrients"] if n["label"] == "Energie"
        )
        assert kcal_summary["value"] == pytest.approx(200.0)

    def test_removed_days_excluded_from_calculation(self):
        """Soft-deleted days are not included in the average."""
        food = make_food(energy_in_kcal_per_100g=100.0)
        plan = MealPlan.objects.create(
            name="P",
            visible_nutrients=["energy_in_kcal"],
            thresholds={},
        )
        active_day = MealPlanDay.objects.create(
            name="Active", meal_plan=plan, removed=False
        )
        removed_day = MealPlanDay.objects.create(
            name="Gone", meal_plan=plan, removed=True
        )
        MealPlanFood.objects.create(
            meal_plan_day=active_day,
            food=food,
            amount_in_g=200.0,
            meal_type="breakfast",
        )
        MealPlanFood.objects.create(
            meal_plan_day=removed_day,
            food=food,
            amount_in_g=999.0,
            meal_type="breakfast",
        )

        ctx = get_meal_plan_context(plan.pk)

        assert ctx["days_count"] == 1
        kcal_summary = next(
            n for n in ctx["summary_nutrients"] if n["label"] == "Energie"
        )
        assert kcal_summary["value"] == pytest.approx(200.0)


@pytest.mark.django_db
class TestGetMealPlanContextThresholds:
    """Threshold logic, status field, ref_val, and percentage tests."""

    def _plan_with_kcal(self, kcal_per_100g, amount_in_g, thresholds):
        food = make_food(energy_in_kcal_per_100g=kcal_per_100g)
        plan = MealPlan.objects.create(
            name="P",
            visible_nutrients=["energy_in_kcal"],
            thresholds=thresholds,
        )
        day = MealPlanDay.objects.create(name="D1", meal_plan=plan)
        MealPlanFood.objects.create(
            meal_plan_day=day, food=food, amount_in_g=amount_in_g, meal_type="breakfast"
        )
        return plan

    def test_both_min_max_within_range_is_ok(self):
        """avg within [min, max] → status='ok', ref_val = midpoint."""
        # avg = 200 kcal, min=100, max=300
        plan = self._plan_with_kcal(
            200.0, 100.0, {"energy_in_kcal": {"min": 100, "max": 300}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")

        assert s["status"] == "ok"
        assert s["reference_val"] == pytest.approx(200.0)  # (100+300)/2
        assert s["threshold_label"] == "100.0 - 300.0"
        assert s["percentage"] == pytest.approx(100, abs=1)

    def test_both_min_max_below_min_alert(self):
        """avg clearly below min (< 95% of min) → status='alert'."""
        # avg = 50 kcal, min=100 → 50 < 95 → alert
        plan = self._plan_with_kcal(
            50.0, 100.0, {"energy_in_kcal": {"min": 100, "max": 300}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")

        assert s["status"] == "alert"

    def test_both_min_max_above_max_alert(self):
        """avg clearly above max (> 105% of max) → status='alert'."""
        # avg = 400 kcal, max=300 → 400 > 315 → alert
        plan = self._plan_with_kcal(
            400.0, 100.0, {"energy_in_kcal": {"min": 100, "max": 300}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")

        assert s["status"] == "alert"

    def test_only_min_set_above_min_is_ok(self):
        """Only min set; avg >= min → status='ok', ref_val = min."""
        plan = self._plan_with_kcal(
            200.0, 100.0, {"energy_in_kcal": {"min": 100, "max": None}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")

        assert s["status"] == "ok"
        assert s["reference_val"] == pytest.approx(100.0)
        assert s["threshold_label"] == "> 100.0"

    def test_only_min_set_below_min_alert(self):
        """Only min set; avg < 95% of min → status='alert'."""
        # avg = 50 kcal, min=100 → 50 < 95 → alert
        plan = self._plan_with_kcal(
            50.0, 100.0, {"energy_in_kcal": {"min": 100, "max": None}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")

        assert s["status"] == "alert"

    def test_only_max_set_below_max_is_ok(self):
        """Only max set; avg <= max → status='ok', ref_val = max."""
        plan = self._plan_with_kcal(
            100.0, 100.0, {"energy_in_kcal": {"min": None, "max": 300}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")

        assert s["status"] == "ok"
        assert s["reference_val"] == pytest.approx(300.0)
        assert s["threshold_label"] == "< 300.0"

    def test_only_max_set_above_max_alert(self):
        """Only max set; avg > 105% of max → status='alert'."""
        # avg = 400 kcal, max=300 → 400 > 315 → alert
        plan = self._plan_with_kcal(
            400.0, 100.0, {"energy_in_kcal": {"min": None, "max": 300}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")

        assert s["status"] == "alert"

    def test_no_threshold_set_is_always_ok(self):
        """When no threshold is set, status='ok' and ref_val = None."""
        plan = self._plan_with_kcal(200.0, 100.0, {})
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")

        assert s["status"] == "ok"
        assert s["reference_val"] is None
        assert s["percentage"] == 0
        assert s["threshold_label"] == ""

    def test_empty_string_thresholds_treated_as_none(self):
        """Empty-string min/max are coerced to None (no TypeError/comparison failure)."""
        # MealPlan.clean() validates against JSON schema which requires number|null,
        # so we bypass full_clean by using update() to set raw empty strings in thresholds.
        plan = MealPlan.objects.create(
            name="P",
            visible_nutrients=["energy_in_kcal"],
            thresholds={},
        )
        food = make_food(energy_in_kcal_per_100g=200.0)
        day = MealPlanDay.objects.create(name="D1", meal_plan=plan)
        MealPlanFood.objects.create(
            meal_plan_day=day, food=food, amount_in_g=100.0, meal_type="breakfast"
        )
        # Directly patch the stored JSON to contain empty strings (legacy data scenario)
        MealPlan.objects.filter(pk=plan.pk).update(
            thresholds={"energy_in_kcal": {"min": "", "max": ""}}
        )
        plan.refresh_from_db()

        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")

        assert s["reference_val"] is None
        assert s["status"] == "ok"

    def test_zero_ref_val_percentage_is_zero(self):
        """ref_val of 0 does not cause ZeroDivisionError; percentage = 0."""
        plan = self._plan_with_kcal(
            200.0, 100.0, {"energy_in_kcal": {"min": 0, "max": 0}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")
        assert s["percentage"] == 0

    def test_percentage_calculation(self):
        """percentage = int((avg / ref_val) * 100)."""
        # avg=200, min=200, max=200 → ref_val=200, percentage=100
        plan = self._plan_with_kcal(
            200.0, 100.0, {"energy_in_kcal": {"min": 200, "max": 200}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")
        assert s["percentage"] == 100

    def test_percentage_half_of_target(self):
        """avg=100, ref_val=200 → percentage=50."""
        plan = self._plan_with_kcal(
            100.0, 100.0, {"energy_in_kcal": {"min": 200, "max": 200}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")
        assert s["percentage"] == 50

    # ------------------------------------------------------------------
    # Warning zone tests (95%–100% of min / 100%–105% of max)
    # ------------------------------------------------------------------

    def test_warn_when_approaching_min_threshold(self):
        """avg in [95% of min, min) → status='warn'."""
        # avg = 97 kcal, min=100 → 97 >= 95 and 97 < 100 → warn
        plan = self._plan_with_kcal(
            97.0, 100.0, {"energy_in_kcal": {"min": 100, "max": None}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")
        assert s["status"] == "warn"

    def test_warn_when_slightly_exceeding_max_threshold(self):
        """avg in (max, 105% of max] → status='warn'."""
        # avg = 310 kcal, max=300 → 310 > 300 and 310 <= 315 → warn
        plan = self._plan_with_kcal(
            310.0, 100.0, {"energy_in_kcal": {"min": None, "max": 300}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")
        assert s["status"] == "warn"

    def test_alert_when_below_95_percent_of_min(self):
        """avg < 95% of min → status='alert' (not warn)."""
        # avg = 94 kcal, min=100 → 94 < 95 → alert
        plan = self._plan_with_kcal(
            94.0, 100.0, {"energy_in_kcal": {"min": 100, "max": None}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")
        assert s["status"] == "alert"

    def test_alert_when_above_105_percent_of_max(self):
        """avg > 105% of max → status='alert' (not warn)."""
        # avg = 316 kcal, max=300 → 316 > 315 → alert
        plan = self._plan_with_kcal(
            316.0, 100.0, {"energy_in_kcal": {"min": None, "max": 300}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")
        assert s["status"] == "alert"

    def test_alert_takes_precedence_over_warn(self):
        """When min breach is alert-level, max warn-level does not downgrade to warn."""
        # avg = 94 kcal (< 95% of min=100), max=90 → 94 in (90, 94.5] → max=warn
        # min breach is alert and takes precedence
        plan = self._plan_with_kcal(
            94.0, 100.0, {"energy_in_kcal": {"min": 100, "max": 90}}
        )
        ctx = get_meal_plan_context(plan.pk)
        s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")
        assert s["status"] == "alert"


@pytest.mark.django_db
class TestGetMealPlanContextStructure:
    """Context structure, visible_nutrients, days_data, and edge cases."""

    def test_empty_plan_no_days_returns_valid_context(self):
        """A plan with no days returns a valid context with zeroed averages."""
        plan = MealPlan.objects.create(
            name="Empty",
            visible_nutrients=["energy_in_kcal"],
            thresholds={},
        )
        ctx = get_meal_plan_context(plan.pk)

        assert ctx["days_count"] == 1  # defaults to 1 to avoid ZeroDivisionError
        assert ctx["days_data"] == []
        assert len(ctx["summary_nutrients"]) >= 1
        kcal_summary = next(
            n for n in ctx["summary_nutrients"] if n["label"] == "Energie"
        )
        assert kcal_summary["value"] == pytest.approx(0.0)

    def test_day_with_no_foods_contributes_zero(self):
        """A day with no foods contributes 0 to all nutrient totals."""
        plan = MealPlan.objects.create(
            name="P",
            visible_nutrients=["energy_in_kcal"],
            thresholds={},
        )
        MealPlanDay.objects.create(name="Empty Day", meal_plan=plan)

        ctx = get_meal_plan_context(plan.pk)

        assert ctx["days_count"] == 1
        kcal_summary = next(
            n for n in ctx["summary_nutrients"] if n["label"] == "Energie"
        )
        assert kcal_summary["value"] == pytest.approx(0.0)

    def test_visible_nutrients_energy_always_present(self):
        """energy_in_kcal is always included in visible_nutrients."""
        plan = MealPlan.objects.create(
            name="P",
            visible_nutrients=["protein_in_g"],  # energy not listed
            thresholds={},
        )
        ctx = get_meal_plan_context(plan.pk)
        labels = [n["label"] for n in ctx["visible_nutrients"]]
        assert "Energie" in labels

    def test_visible_nutrients_respects_plan_setting(self):
        """Only nutrients in visible_nutrients (plus energy) appear in summary."""
        plan = MealPlan.objects.create(
            name="P",
            visible_nutrients=["protein_in_g"],
            thresholds={},
        )
        ctx = get_meal_plan_context(plan.pk)
        labels = [n["label"] for n in ctx["summary_nutrients"]]
        assert "Protein" in labels
        assert "Energie" in labels
        # A nutrient not in visible_nutrients should be absent
        assert "Fett" not in labels

    def test_all_nutrients_always_returned(self):
        """all_nutrients always contains all 15 nutrients regardless of visibility."""
        from meals.nutrients import NUTRIENTS

        plan = MealPlan.objects.create(
            name="P",
            visible_nutrients=["energy_in_kcal"],
            thresholds={},
        )
        ctx = get_meal_plan_context(plan.pk)
        assert len(ctx["all_nutrients"]) == len(NUTRIENTS)

    def test_days_data_meal_grouping(self):
        """Foods are correctly grouped by meal type in days_data."""
        food = make_food(energy_in_kcal_per_100g=100.0)
        plan = MealPlan.objects.create(
            name="P",
            visible_nutrients=["energy_in_kcal"],
            thresholds={},
        )
        day = MealPlanDay.objects.create(name="D1", meal_plan=plan)
        MealPlanFood.objects.create(
            meal_plan_day=day, food=food, amount_in_g=100.0, meal_type="breakfast"
        )

        ctx = get_meal_plan_context(plan.pk)

        assert len(ctx["days_data"]) == 1
        meals = ctx["days_data"][0]["meals"]
        assert len(meals["Frühstück"]) == 1
        assert len(meals["Mittagessen"]) == 0
        assert len(meals["Abendessen"]) == 0

    def test_plan_object_included_in_context(self):
        """The plan object itself is present in the returned context."""
        plan = MealPlan.objects.create(
            name="My Plan", visible_nutrients=[], thresholds={}
        )
        ctx = get_meal_plan_context(plan.pk)
        assert ctx["plan"].pk == plan.pk
        assert ctx["plan"].name == "My Plan"

    def test_multiple_nutrients_calculated_independently(self):
        """Protein and kcal are each calculated and averaged independently."""
        food = make_food(energy_in_kcal_per_100g=300.0, protein_in_g_per_100g=20.0)
        plan = MealPlan.objects.create(
            name="P",
            visible_nutrients=["energy_in_kcal", "protein_in_g"],
            thresholds={},
        )
        day = MealPlanDay.objects.create(name="D1", meal_plan=plan)
        MealPlanFood.objects.create(
            meal_plan_day=day, food=food, amount_in_g=200.0, meal_type="dinner"
        )

        ctx = get_meal_plan_context(plan.pk)

        kcal_s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Energie")
        prot_s = next(n for n in ctx["summary_nutrients"] if n["label"] == "Protein")

        assert kcal_s["value"] == pytest.approx(600.0)  # 300 * 200/100
        assert prot_s["value"] == pytest.approx(40.0)  # 20 * 200/100
