from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0023_food_molybdenum_in_mug_per_100g_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='food',
            name='data_source',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]
