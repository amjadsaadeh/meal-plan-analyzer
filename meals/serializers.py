from rest_framework import serializers
from .models import Food, MealPlan, MealPlanDay, MealPlanFood, ThresholdPreset


class FoodSerializer(serializers.ModelSerializer):
    # Populated by FoodViewSet.list() when an alias caused this food to appear
    # in search results. None when the food matched by name/bls_code directly.
    matched_alias = serializers.SerializerMethodField()

    class Meta:
        model = Food
        fields = [
            'id', 'bls_code', 'name',
            'energy_in_kj_per_100g', 'energy_in_kcal_per_100g',
            'protein_in_g_per_100g', 'fat_in_g_per_100g',
            'carbohydrate_in_g_per_100g', 'fibre_in_g_per_100g',
            'iron_in_mg_per_100g', 'sugar_in_g_per_100g',
            'omega3_in_g_per_100g', 'vitc_in_mg_per_100g',
            'magnesium_in_mg_per_100g', 'zinc_in_mg_per_100g',
            'vitb12_in_mug_per_100g', 'vita_in_mug_per_100g',
            'calcium_in_mg_per_100g', 'vitd_in_mug_per_100g',
            'vitb1_in_mg_per_100g', 'vitb2_in_mg_per_100g',
            'vitb3_in_mg_per_100g', 'vitb5_in_mg_per_100g',
            'vitb6_in_mug_per_100g', 'biotin_in_mug_per_100g',
            'iodine_in_mug_per_100g', 'copper_in_mug_per_100g',
            'manganese_in_mug_per_100g',
            'matched_alias',
        ]

    def get_matched_alias(self, obj):
        return getattr(obj, 'matched_alias', None)

class ThresholdPresetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThresholdPreset
        fields = '__all__'

class MealPlanFoodSerializer(serializers.ModelSerializer):
    food_name = serializers.ReadOnlyField(source='food.name')
    food_bls_code = serializers.ReadOnlyField(source='food.bls_code')
    food_data = FoodSerializer(source='food', read_only=True)

    class Meta:
        model = MealPlanFood
        fields = ['id', 'meal_plan_day', 'food', 'food_name', 'food_bls_code', 'food_data', 'amount_in_g', 'meal_type', 'export_name']

    def validate_amount_in_g(self, value):
        if value < 0:
            raise serializers.ValidationError("Amount must be 0 or greater.")
        return value

class MealPlanDaySerializer(serializers.ModelSerializer):
    foods = MealPlanFoodSerializer(source='mealplanfood_set', many=True, read_only=True)
    
    class Meta:
        model = MealPlanDay
        fields = ['id', 'name', 'creation_date', 'change_date', 'foods', 'meal_plan', 'removed']

class MealPlanSerializer(serializers.ModelSerializer):
    days = MealPlanDaySerializer(many=True, read_only=True)

    class Meta:
        model = MealPlan
        fields = ['id', 'name', 'subtitle', 'creation_date', 'change_date', 'days', 'visible_nutrients', 'thresholds']

    def validate(self, attrs):
        """
        Perform model-level validation to catch Django's ValidationError
        and convert it to DRF's ValidationError (avoiding 500 errors).
        """
        instance = MealPlan(**attrs)
        try:
            instance.full_clean()
        except serializers.ValidationError as e:
            raise e
        except Exception as e:
            from django.core.exceptions import ValidationError as DjangoValidationError
            if isinstance(e, DjangoValidationError):
                raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.message)
            raise e
        return attrs
