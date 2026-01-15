from rest_framework import serializers
from .models import Food, MealPlanDay, MealPlanFood

class FoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Food
        fields = '__all__'

class MealPlanFoodSerializer(serializers.ModelSerializer):
    food_name = serializers.ReadOnlyField(source='food.name')
    food_bls_code = serializers.ReadOnlyField(source='food.bls_code')
    
    class Meta:
        model = MealPlanFood
        fields = ['id', 'meal_plan_day', 'food', 'food_name', 'food_bls_code', 'amount_in_g', 'meal_type']

class MealPlanDaySerializer(serializers.ModelSerializer):
    foods = MealPlanFoodSerializer(source='mealplanfood_set', many=True, read_only=True)
    
    class Meta:
        model = MealPlanDay
        fields = ['id', 'name', 'creation_date', 'change_date', 'foods', 'visible_nutrients']
