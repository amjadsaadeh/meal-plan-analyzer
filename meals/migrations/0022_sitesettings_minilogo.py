from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("meals", "0021_food_biotin_in_mug_per_100g_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="minilogo",
            field=models.FileField(
                blank=True,
                help_text="Small logo (50×50 px) shown on the top-right of every PDF page except the first.",
                null=True,
                upload_to="logos/",
            ),
        ),
    ]
