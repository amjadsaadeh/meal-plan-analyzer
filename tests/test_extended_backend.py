import pytest
from django.urls import reverse
from rest_framework import status
from django.utils import translation
from meals.models import Food, MealPlan, MealPlanDay, MealPlanFood, ThresholdPreset
from meals.views import get_meal_plan_context


@pytest.fixture(autouse=True)
def set_german_locale():
    translation.activate("de")
    yield
    translation.deactivate()


@pytest.mark.django_db
class TestExtendedMealPlanLogic:
    def test_meal_plan_summary_with_missing_nutrients(self, authenticated_client):
        """
        Verify that averages are correct when one food has a nutrient and another doesn't.
        """
        # Food A: 10g protein/100g
        # Food B: 0g protein/100g
        food_a = Food.objects.create(
            bls_code="A",
            name="Protein Heavy",
            protein_in_g_per_100g=10.0,
            energy_in_kj_per_100g=0,
            energy_in_kcal_per_100g=0,
        )
        food_b = Food.objects.create(
            bls_code="B",
            name="Protein Light",
            protein_in_g_per_100g=0.0,
            energy_in_kj_per_100g=0,
            energy_in_kcal_per_100g=0,
        )

        plan = MealPlan.objects.create(
            name="Balanced Plan", visible_nutrients=["protein_in_g"]
        )
        day = MealPlanDay.objects.create(name="Day 1", meal_plan=plan)

        # 100g of A (10g protein) + 100g of B (0g protein) = 10g protein total for the day
        MealPlanFood.objects.create(
            meal_plan_day=day, food=food_a, amount_in_g=100.0, meal_type="breakfast"
        )
        MealPlanFood.objects.create(
            meal_plan_day=day, food=food_b, amount_in_g=100.0, meal_type="lunch"
        )

        ctx = get_meal_plan_context(plan.pk)
        prot_summary = next(
            n for n in ctx["summary_nutrients"] if n["label"] == "Protein"
        )
        assert prot_summary["value"] == 10.0

    def test_search_multiple_terms_relevance(self, authenticated_client):
        """
        Verify that search with multiple terms works and respects relevance.
        """
        Food.objects.create(
            bls_code="F1",
            name="Red Apple",
            energy_in_kj_per_100g=0,
            energy_in_kcal_per_100g=0,
        )
        Food.objects.create(
            bls_code="F2",
            name="Green Apple",
            energy_in_kj_per_100g=0,
            energy_in_kcal_per_100g=0,
        )
        Food.objects.create(
            bls_code="F3",
            name="Red Tomato",
            energy_in_kj_per_100g=0,
            energy_in_kcal_per_100g=0,
        )

        url = reverse("food-list")
        response = authenticated_client.get(url, {"search": "Red Apple"})
        assert response.status_code == status.HTTP_200_OK

        # "Red Apple" should be first (exact match or most terms matching)
        names = [item["name"] for item in response.data["results"]]
        assert names[0] == "Red Apple"
        assert "Green Apple" in names
        assert "Red Tomato" in names

    def test_apply_threshold_preset(self, authenticated_client):
        """
        Verify that patching a MealPlan with data from a ThresholdPreset works.
        """
        preset = ThresholdPreset.objects.create(
            name="Weight Gain", energy_in_kcal_min=3000, energy_in_kcal_max=4000
        )
        plan = MealPlan.objects.create(name="My Plan")

        # Simulate frontend applying preset
        thresholds = {
            "energy_in_kcal": {
                "min": preset.energy_in_kcal_min,
                "max": preset.energy_in_kcal_max,
            }
        }

        url = reverse("mealplan-detail", kwargs={"pk": plan.pk})
        # Wait, the endpoint for MealPlan is /api/mealplans/
        api_url = f"/api/mealplans/{plan.pk}/"
        response = authenticated_client.patch(
            api_url, {"thresholds": thresholds}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.thresholds["energy_in_kcal"]["min"] == 3000

    def test_export_name_persistence_in_context(self, authenticated_client):
        """
        Verify that export_name is correctly passed to the PDF context.
        """
        food = Food.objects.create(
            bls_code="E1",
            name="Original Name",
            energy_in_kj_per_100g=0,
            energy_in_kcal_per_100g=0,
        )
        plan = MealPlan.objects.create(name="Export Plan")
        day = MealPlanDay.objects.create(name="Day 1", meal_plan=plan)
        MealPlanFood.objects.create(
            meal_plan_day=day,
            food=food,
            amount_in_g=100.0,
            meal_type="breakfast",
            export_name="Fancy Name",
        )

        ctx = get_meal_plan_context(plan.pk)
        day_info = ctx["days_data"][0]
        # In context, meals are a dict of lists
        breakfast_items = day_info["meals"][translation.gettext("Breakfast")]
        assert breakfast_items[0]["export_name"] == "Fancy Name"
        assert breakfast_items[0]["food"].name == "Original Name"
