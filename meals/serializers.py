from rest_framework import serializers
from .models import Food, MealPlan, MealPlanFood

class FoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Food
        fields = '__all__'

class MealPlanFoodSerializer(serializers.ModelSerializer):
    food_name = serializers.ReadOnlyField(source='food.name')
    food_bls_code = serializers.ReadOnlyField(source='food.bls_code')
    
    class Meta:
        model = MealPlanFood
        fields = ['id', 'meal_plan', 'food', 'food_name', 'food_bls_code', 'amount_in_g']

class MealPlanSerializer(serializers.ModelSerializer):
    foods = MealPlanFoodSerializer(source='mealplanfood_set', many=True, read_only=True)
    
    class Meta:
        model = MealPlan
        fields = ['id', 'name', 'creation_date', 'change_date', 'foods']
