import meals.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("meals", "0027_food_water_in_g_per_100g"),
    ]

    operations = [
        migrations.AlterField(
            model_name="backgroundjob",
            name="result_file",
            field=models.FileField(
                blank=True,
                null=True,
                storage=meals.storage.PrivateExportsStorage(),
            ),
        ),
    ]
