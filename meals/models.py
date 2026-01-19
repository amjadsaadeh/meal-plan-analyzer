from django.db import models

class Food(models.Model):
    bls_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    energy_in_kj_per_100g = models.FloatField()
    energy_in_kcal_per_100g = models.FloatField()
    protein_in_g_per_100g = models.FloatField(default=0.0)
    fat_in_g_per_100g = models.FloatField(default=0.0)
    carbohydrate_in_g_per_100g = models.FloatField(default=0.0)
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

class ThresholdPreset(models.Model):
    name = models.CharField(max_length=255, unique=True)
    
    energy_in_kj_min = models.FloatField(null=True, blank=True)
    energy_in_kj_max = models.FloatField(null=True, blank=True)
    
    energy_in_kcal_min = models.FloatField(null=True, blank=True)
    energy_in_kcal_max = models.FloatField(null=True, blank=True)
    
    protein_in_g_min = models.FloatField(null=True, blank=True)
    protein_in_g_max = models.FloatField(null=True, blank=True)
    
    fat_in_g_min = models.FloatField(null=True, blank=True)
    fat_in_g_max = models.FloatField(null=True, blank=True)
    
    carbohydrate_in_g_min = models.FloatField(null=True, blank=True)
    carbohydrate_in_g_max = models.FloatField(null=True, blank=True)
    
    fibre_in_g_min = models.FloatField(null=True, blank=True)
    fibre_in_g_max = models.FloatField(null=True, blank=True)
    
    iron_in_mg_min = models.FloatField(null=True, blank=True)
    iron_in_mg_max = models.FloatField(null=True, blank=True)
    
    sugar_in_g_min = models.FloatField(null=True, blank=True)
    sugar_in_g_max = models.FloatField(null=True, blank=True)
    
    omega3_in_g_min = models.FloatField(null=True, blank=True)
    omega3_in_g_max = models.FloatField(null=True, blank=True)
    
    vitc_in_mg_min = models.FloatField(null=True, blank=True)
    vitc_in_mg_max = models.FloatField(null=True, blank=True)
    
    magnesium_in_mg_min = models.FloatField(null=True, blank=True)
    magnesium_in_mg_max = models.FloatField(null=True, blank=True)
    
    zinc_in_mg_min = models.FloatField(null=True, blank=True)
    zinc_in_mg_max = models.FloatField(null=True, blank=True)
    
    vitb12_in_mug_min = models.FloatField(null=True, blank=True)
    vitb12_in_mug_max = models.FloatField(null=True, blank=True)
    
    vita_in_mug_min = models.FloatField(null=True, blank=True)
    vita_in_mug_max = models.FloatField(null=True, blank=True)
    
    calcium_in_mg_min = models.FloatField(null=True, blank=True)
    calcium_in_mg_max = models.FloatField(null=True, blank=True)
    
    vitd_in_mug_min = models.FloatField(null=True, blank=True)
    vitd_in_mug_max = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name


class MealPlan(models.Model):
    name = models.CharField(max_length=255, default="Neuer Plan")
    creation_date = models.DateTimeField(auto_now_add=True)
    change_date = models.DateTimeField(auto_now=True)
    visible_nutrients = models.JSONField(default=list, blank=True)
    thresholds = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-creation_date']

    def __str__(self):
        return self.name

class MealPlanDay(models.Model):
    name = models.CharField(max_length=255, default="Neuer Tag")
    meal_plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE, related_name='days', null=True, blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    change_date = models.DateTimeField(auto_now=True)
    foods = models.ManyToManyField(Food, through='MealPlanFood', related_name='meal_plan_days')


    class Meta:
        ordering = ['-creation_date']

    def __str__(self):
        return self.name

class MealPlanFood(models.Model):
    class MealType(models.TextChoices):
        BREAKFAST = "breakfast", "Breakfast"
        LUNCH = "lunch", "Lunch"
        DINNER = "dinner", "Dinner"

    meal_plan_day = models.ForeignKey(MealPlanDay, on_delete=models.CASCADE)
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    amount_in_g = models.FloatField()
    meal_type = models.CharField(
        max_length=20,
        choices=MealType.choices,
        default=MealType.BREAKFAST
    )
    
    class Meta:
        unique_together = ('meal_plan_day', 'food', 'meal_type')
