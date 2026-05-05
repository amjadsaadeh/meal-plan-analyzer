from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import (
    Food,
    FoodAlias,
    MealPlan,
    MealPlanDay,
    MealPlanFood,
    ThresholdPreset,
    BackgroundJob,
)


class FoodSerializer(serializers.ModelSerializer):
    # Populated by FoodViewSet.list() when an alias caused this food to appear
    # in search results. None when the food matched by name/bls_code directly.
    matched_alias = serializers.SerializerMethodField()

    class Meta:
        model = Food
        fields = [
            "id",
            "bls_code",
            "name",
            "energy_in_kj_per_100g",
            "energy_in_kcal_per_100g",
            "water_in_g_per_100g",
            "protein_in_g_per_100g",
            "fat_in_g_per_100g",
            "carbohydrate_in_g_per_100g",
            "fibre_in_g_per_100g",
            "iron_in_mg_per_100g",
            "sugar_in_g_per_100g",
            "omega3_in_g_per_100g",
            "vitc_in_mg_per_100g",
            "magnesium_in_mg_per_100g",
            "zinc_in_mg_per_100g",
            "vitb12_in_mug_per_100g",
            "vita_in_mug_per_100g",
            "calcium_in_mg_per_100g",
            "vitd_in_mug_per_100g",
            "vitb1_in_mg_per_100g",
            "vitb2_in_mg_per_100g",
            "vitb3_in_mg_per_100g",
            "vitb5_in_mg_per_100g",
            "vitb6_in_mug_per_100g",
            "biotin_in_mug_per_100g",
            "iodine_in_mug_per_100g",
            "copper_in_mug_per_100g",
            "manganese_in_mug_per_100g",
            "molybdenum_in_mug_per_100g",
            "data_source",
            "matched_alias",
        ]

    def get_matched_alias(self, obj):
        return getattr(obj, "matched_alias", None)

    def validate(self, data):
        """
        Ensure that only one of kcal or kj is provided in a single request.
        """
        kcal = data.get("energy_in_kcal_per_100g")
        kj = data.get("energy_in_kj_per_100g")

        if kcal is not None and kj is not None:
            raise serializers.ValidationError(
                "Cannot set both energy_in_kj_per_100g and energy_in_kcal_per_100g at the same time."
            )

        if kcal is not None:
            if kcal < 0:
                raise serializers.ValidationError(
                    {"energy_in_kcal_per_100g": "Must be 0 or greater."}
                )
            data["energy_in_kj_per_100g"] = round(kcal * 4.184, 1)
        elif kj is not None:
            if kj < 0:
                raise serializers.ValidationError(
                    {"energy_in_kj_per_100g": "Must be 0 or greater."}
                )
            data["energy_in_kcal_per_100g"] = round(kj / 4.184, 1)

        return data


class FoodAliasSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodAlias
        fields = ["id", "food", "alias"]


class ThresholdPresetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThresholdPreset
        fields = "__all__"

    def validate(self, data):
        errors = {}
        for field in ThresholdPreset._meta.get_fields():
            if not field.name.endswith("_min"):
                continue
            base = field.name[:-4]  # strip "_min"
            max_field = base + "_max"
            if self.instance is not None:
                min_val = data.get(field.name, getattr(self.instance, field.name))
                max_val = data.get(max_field, getattr(self.instance, max_field))
            else:
                min_val = data.get(field.name)
                max_val = data.get(max_field)
            if min_val is not None and max_val is not None and min_val >= max_val:
                errors[field.name] = f"Must be less than max ({max_val})."
        if errors:
            raise serializers.ValidationError(errors)
        return data


class MealPlanFoodSerializer(serializers.ModelSerializer):
    food_name = serializers.ReadOnlyField(source="food.name")
    food_bls_code = serializers.ReadOnlyField(source="food.bls_code")
    food_data = FoodSerializer(source="food", read_only=True)

    class Meta:
        model = MealPlanFood
        fields = [
            "id",
            "meal_plan_day",
            "food",
            "food_name",
            "food_bls_code",
            "food_data",
            "amount_in_g",
            "meal_type",
            "export_name",
        ]

    def validate_amount_in_g(self, value):
        if value < 0:
            raise serializers.ValidationError("Amount must be 0 or greater.")
        return value


class MealPlanDaySerializer(serializers.ModelSerializer):
    foods = MealPlanFoodSerializer(source="mealplanfood_set", many=True, read_only=True)

    class Meta:
        model = MealPlanDay
        fields = [
            "id",
            "name",
            "creation_date",
            "change_date",
            "foods",
            "meal_plan",
            "removed",
        ]


class MealPlanSerializer(serializers.ModelSerializer):
    days = MealPlanDaySerializer(many=True, read_only=True)

    class Meta:
        model = MealPlan
        fields = [
            "id",
            "name",
            "subtitle",
            "creation_date",
            "change_date",
            "days",
            "visible_nutrients",
            "thresholds",
        ]

    def validate(self, attrs):
        instance = MealPlan(**attrs)
        try:
            instance.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(
                e.message_dict if hasattr(e, "message_dict") else e.messages
            )
        return attrs


class BackgroundJobCreateSerializer(serializers.Serializer):
    meal_plan_id = serializers.IntegerField()

    def validate_meal_plan_id(self, value):
        if not MealPlan.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Meal plan not found.")
        return value


class BackgroundJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackgroundJob
        fields = [
            "id",
            "status",
            "progress",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "progress",
            "error_message",
            "created_at",
            "updated_at",
        ]
