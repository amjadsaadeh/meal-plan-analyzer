from django.db import models

class Food(models.Model):
    bls_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    energy_in_kj_per_100g = models.FloatField()
    energy_in_kcal_per_100g = models.FloatField()

    def __str__(self):
        return self.name

class MealPlan(models.Model):
    name = models.CharField(max_length=255)
    creation_date = models.DateTimeField(auto_now_add=True)
    change_date = models.DateTimeField(auto_now=True)
    foods = models.ManyToManyField(Food, through='MealPlanFood', related_name='meal_plans')

    def __str__(self):
        return self.name

class MealPlanFood(models.Model):
    meal_plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE)
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('meal_plan', 'food')
