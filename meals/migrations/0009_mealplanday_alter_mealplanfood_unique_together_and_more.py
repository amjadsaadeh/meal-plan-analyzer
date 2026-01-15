from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0008_alter_mealplanfood_unique_together_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='MealPlan',
            new_name='MealPlanDay',
        ),
        migrations.RenameField(
            model_name='MealPlanFood',
            old_name='meal_plan',
            new_name='meal_plan_day',
        ),
        migrations.AlterField(
            model_name='mealplanday',
            name='foods',
            field=models.ManyToManyField(related_name='meal_plan_days', through='meals.MealPlanFood', to='meals.food'),
        ),
        migrations.AlterUniqueTogether(
            name='mealplanfood',
            unique_together={('meal_plan_day', 'food', 'meal_type')},
        ),
    ]
