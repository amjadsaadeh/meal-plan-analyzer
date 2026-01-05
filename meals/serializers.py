from rest_framework import serializers
from .models import Food, MealPlan, MealPlanFood

class FoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Food
        fields = '__all__'

class MealPlanFoodSerializer(serializers.ModelSerializer):
    food_name = serializers.ReadOnlyField(source='food.name')
    
    class Meta:
        model = MealPlanFood
        fields = ['id', 'food', 'food_name']

class MealPlanSerializer(serializers.ModelSerializer):
    foods = FoodSerializer(many=True, read_only=True)
    
    class Meta:
        model = MealPlan
        fields = ['id', 'name', 'creation_date', 'change_date', 'foods']
