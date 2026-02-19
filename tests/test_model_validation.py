"""
Tests for MealPlan model validation and clean() method.

Covers:
  - Legacy nutrient key migration in visible_nutrients and thresholds
  - THRESHOLD_SCHEMA validation (invalid formats raise ValidationError)
  - Default values for name, visible_nutrients, and thresholds
  - save() always calls full_clean()
  - __str__ representation
"""

import pytest
from django.core.exceptions import ValidationError
from meals.models import MealPlan, SiteSettings
from meals.nutrients import NUTRIENT_IDS


@pytest.mark.django_db
class TestMealPlanDefaults:
    """Default values are set correctly on creation."""

    def test_default_name(self):
        plan = MealPlan.objects.create()
        assert plan.name == "Neuer Plan"

    def test_default_visible_nutrients_contains_all_ids(self):
        plan = MealPlan.objects.create()
        assert sorted(plan.visible_nutrients) == sorted(NUTRIENT_IDS)

    def test_default_thresholds_is_empty_dict(self):
        plan = MealPlan.objects.create()
        assert plan.thresholds == {}

    def test_str_returns_name(self):
        plan = MealPlan.objects.create(name="Mein Plan")
        assert str(plan) == "Mein Plan"


@pytest.mark.django_db
class TestMealPlanCleanNutrientMigration:
    """
    MealPlan.clean() migrates legacy nutrient key names to current ones.
    Verified via save() → full_clean() → clean().
    """

    # --- visible_nutrients migrations ---

    def test_visible_nutrients_protein_migrated(self):
        plan = MealPlan.objects.create(visible_nutrients=["protein"])
        assert "protein_in_g" in plan.visible_nutrients
        assert "protein" not in plan.visible_nutrients

    def test_visible_nutrients_kcal_migrated(self):
        plan = MealPlan.objects.create(visible_nutrients=["kcal"])
        assert "energy_in_kcal" in plan.visible_nutrients
        assert "kcal" not in plan.visible_nutrients

    def test_visible_nutrients_multiple_old_keys_migrated(self):
        old_keys = ["protein", "fat", "omega3", "carbs", "sugar",
                    "fibre", "iron", "vitc", "magnesium", "zinc",
                    "vitb12", "vita", "calcium", "vitd", "kcal"]
        expected = ["protein_in_g", "fat_in_g", "omega3_in_g", "carbohydrate_in_g",
                    "sugar_in_g", "fibre_in_g", "iron_in_mg", "vitc_in_mg",
                    "magnesium_in_mg", "zinc_in_mg", "vitb12_in_mug", "vita_in_mug",
                    "calcium_in_mg", "vitd_in_mug", "energy_in_kcal"]
        plan = MealPlan.objects.create(visible_nutrients=old_keys)
        assert sorted(plan.visible_nutrients) == sorted(expected)

    def test_visible_nutrients_already_new_keys_unchanged(self):
        plan = MealPlan.objects.create(visible_nutrients=["protein_in_g", "energy_in_kcal"])
        assert "protein_in_g" in plan.visible_nutrients
        assert "energy_in_kcal" in plan.visible_nutrients

    # --- thresholds key migrations ---

    def test_thresholds_old_key_migrated(self):
        plan = MealPlan.objects.create(thresholds={"protein": {"min": 50, "max": 100}})
        assert "protein_in_g" in plan.thresholds
        assert "protein" not in plan.thresholds

    def test_thresholds_kcal_key_migrated(self):
        plan = MealPlan.objects.create(thresholds={"kcal": {"min": 2000, "max": 2500}})
        assert "energy_in_kcal" in plan.thresholds
        assert "kcal" not in plan.thresholds

    def test_thresholds_new_key_unchanged(self):
        plan = MealPlan.objects.create(
            thresholds={"energy_in_kcal": {"min": 2000, "max": 2500}}
        )
        assert plan.thresholds["energy_in_kcal"] == {"min": 2000, "max": 2500}

    def test_thresholds_values_preserved_after_migration(self):
        plan = MealPlan.objects.create(
            thresholds={"protein": {"min": 55.0, "max": 120.0}}
        )
        assert plan.thresholds["protein_in_g"]["min"] == 55.0
        assert plan.thresholds["protein_in_g"]["max"] == 120.0


@pytest.mark.django_db
class TestMealPlanThresholdValidation:
    """THRESHOLD_SCHEMA is validated on save; invalid data raises ValidationError."""

    def test_valid_thresholds_accepted(self):
        plan = MealPlan(
            thresholds={"energy_in_kcal": {"min": 1800, "max": 2500}}
        )
        plan.full_clean()  # should not raise

    def test_null_min_max_accepted(self):
        plan = MealPlan(
            thresholds={"energy_in_kcal": {"min": None, "max": None}}
        )
        plan.full_clean()  # should not raise

    def test_unknown_nutrient_key_rejected(self):
        plan = MealPlan(thresholds={"unknown_nutrient": {"min": 10, "max": 50}})
        with pytest.raises(ValidationError, match="Invalid thresholds"):
            plan.full_clean()

    def test_wrong_value_type_rejected(self):
        """String values where numbers are expected should fail schema validation."""
        plan = MealPlan(thresholds={"energy_in_kcal": {"min": "lots", "max": "few"}})
        with pytest.raises(ValidationError, match="Invalid thresholds"):
            plan.full_clean()

    def test_extra_property_in_threshold_entry_rejected(self):
        """Additional properties beyond min/max are not allowed by schema."""
        plan = MealPlan(
            thresholds={"energy_in_kcal": {"min": 100, "max": 200, "target": 150}}
        )
        with pytest.raises(ValidationError, match="Invalid thresholds"):
            plan.full_clean()

    def test_empty_thresholds_accepted(self):
        plan = MealPlan(thresholds={})
        plan.full_clean()  # should not raise

    def test_save_triggers_full_clean(self):
        """save() must call full_clean(), so invalid data raises ValidationError on save."""
        plan = MealPlan(thresholds={"bad_key": {"min": 0, "max": 1}})
        with pytest.raises(ValidationError):
            plan.save()


@pytest.mark.django_db
class TestSiteSettingsSingleton:
    """SiteSettings enforces a singleton pattern via pk=1."""

    def test_get_creates_instance_when_none_exists(self):
        assert SiteSettings.objects.count() == 0
        obj = SiteSettings.get()
        assert obj.pk == 1
        assert SiteSettings.objects.count() == 1

    def test_get_returns_existing_instance(self):
        SiteSettings.objects.create()
        obj = SiteSettings.get()
        assert obj.pk == 1
        assert SiteSettings.objects.count() == 1

    def test_save_forces_pk_1(self):
        s = SiteSettings()
        s.save()
        assert s.pk == 1

    def test_only_one_instance_after_multiple_saves(self):
        SiteSettings().save()
        SiteSettings().save()
        assert SiteSettings.objects.count() == 1

    def test_logo_field_is_blank_by_default(self):
        obj = SiteSettings.get()
        assert not obj.logo
