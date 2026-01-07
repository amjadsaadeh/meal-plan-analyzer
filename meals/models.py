from django.db import models

class Food(models.Model):
    bls_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    energy_in_kj_per_100g = models.FloatField()
    energy_in_kcal_per_100g = models.FloatField()
    protein_in_g_per_100g = models.FloatField(default=0.0)
    fat_in_g_per_100g = models.FloatField(default=0.0)
    fibre_in_g_per_100g = models.FloatField(default=0.0)
    iron_in_mg_per_100g = models.FloatField(default=0.0)
    sugar_in_g_per_100g = models.FloatField(default=0.0)
    omega3_in_g_per_100g = models.FloatField(default=0.0)
    vitc_in_mg_per_100g = models.FloatField(default=0.0)
    magnesium_in_mg_per_100g = models.FloatField(default=0.0)
    zinc_in_mg_per_100g = models.FloatField(default=0.0)
    vitb12_in_mug_per_100g = models.FloatField(default=0.0)
    vita_in_mug_per_100g = models.FloatField(default=0.0)
    calcium_in_mg_per_100g = models.FloatField(default=0.0)
    vitd_in_mug_per_100g = models.FloatField(default=0.0)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class MealPlan(models.Model):
    name = models.CharField(max_length=255, default="Neuer Plan")
    creation_date = models.DateTimeField(auto_now_add=True)
    change_date = models.DateTimeField(auto_now=True)
    foods = models.ManyToManyField(Food, through='MealPlanFood', related_name='meal_plans')

    class Meta:
        ordering = ['-creation_date']

    def __str__(self):
        return self.name

class MealPlanFood(models.Model):
    meal_plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE)
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    amount_in_g = models.FloatField()
    
    class Meta:
        unique_together = ('meal_plan', 'food')
