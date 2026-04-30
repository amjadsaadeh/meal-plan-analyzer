import uuid

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import jsonschema
from .nutrients import THRESHOLD_SCHEMA, NUTRIENT_IDS
from .storage import PrivateExportsStorage

ALIAS_CACHE_KEY = "food_aliases_index"


def get_alias_index():
    """Return a cached dict mapping food_id → list[alias_string].

    The index is built from FoodAlias rows on the first call and then stored
    in Django's cache backend for up to one hour to keep database load low.
    Cache-invalidation signals (see bottom of file) clear the entry whenever
    any FoodAlias row is created, changed, or deleted.
    """
    index = cache.get(ALIAS_CACHE_KEY)
    if index is None:
        index = {}
        for fa in FoodAlias.objects.select_related("food").values("food_id", "alias"):
            index.setdefault(fa["food_id"], []).append(fa["alias"])
        cache.set(ALIAS_CACHE_KEY, index, timeout=3600)
    return index


class Food(models.Model):
    bls_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    energy_in_kj_per_100g = models.FloatField()
    energy_in_kcal_per_100g = models.FloatField()
    water_in_g_per_100g = models.FloatField(default=0.0)
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
    vitb1_in_mg_per_100g = models.FloatField(default=0.0)
    vitb2_in_mg_per_100g = models.FloatField(default=0.0)
    vitb3_in_mg_per_100g = models.FloatField(default=0.0)
    vitb5_in_mg_per_100g = models.FloatField(default=0.0)
    vitb6_in_mug_per_100g = models.FloatField(default=0.0)
    biotin_in_mug_per_100g = models.FloatField(default=0.0)
    iodine_in_mug_per_100g = models.FloatField(default=0.0)
    copper_in_mug_per_100g = models.FloatField(default=0.0)
    manganese_in_mug_per_100g = models.FloatField(default=0.0)
    molybdenum_in_mug_per_100g = models.FloatField(default=0.0)
    data_source = models.CharField(max_length=100, default="", blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ThresholdPreset(models.Model):
    name = models.CharField(max_length=255, unique=True)

    energy_in_kj_min = models.FloatField(null=True, blank=True)
    energy_in_kj_max = models.FloatField(null=True, blank=True)

    energy_in_kcal_min = models.FloatField(null=True, blank=True)
    energy_in_kcal_max = models.FloatField(null=True, blank=True)

    water_in_g_min = models.FloatField(null=True, blank=True)
    water_in_g_max = models.FloatField(null=True, blank=True)

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

    vitb1_in_mg_min = models.FloatField(null=True, blank=True)
    vitb1_in_mg_max = models.FloatField(null=True, blank=True)

    vitb2_in_mg_min = models.FloatField(null=True, blank=True)
    vitb2_in_mg_max = models.FloatField(null=True, blank=True)

    vitb3_in_mg_min = models.FloatField(null=True, blank=True)
    vitb3_in_mg_max = models.FloatField(null=True, blank=True)

    vitb5_in_mg_min = models.FloatField(null=True, blank=True)
    vitb5_in_mg_max = models.FloatField(null=True, blank=True)

    vitb6_in_mug_min = models.FloatField(null=True, blank=True)
    vitb6_in_mug_max = models.FloatField(null=True, blank=True)

    biotin_in_mug_min = models.FloatField(null=True, blank=True)
    biotin_in_mug_max = models.FloatField(null=True, blank=True)

    iodine_in_mug_min = models.FloatField(null=True, blank=True)
    iodine_in_mug_max = models.FloatField(null=True, blank=True)

    copper_in_mug_min = models.FloatField(null=True, blank=True)
    copper_in_mug_max = models.FloatField(null=True, blank=True)

    manganese_in_mug_min = models.FloatField(null=True, blank=True)
    manganese_in_mug_max = models.FloatField(null=True, blank=True)

    molybdenum_in_mug_min = models.FloatField(null=True, blank=True)
    molybdenum_in_mug_max = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name


def get_default_visible_nutrients():
    return list(NUTRIENT_IDS)


class MealPlan(models.Model):
    name = models.CharField(max_length=255, default="Neuer Plan")
    subtitle = models.CharField(max_length=500, blank=True, default="")
    creation_date = models.DateTimeField(auto_now_add=True)
    change_date = models.DateTimeField(auto_now=True)
    visible_nutrients = models.JSONField(
        default=get_default_visible_nutrients, blank=True
    )
    thresholds = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-creation_date"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        # Migrate old nutrient names if present
        migration_map = {
            "protein": "protein_in_g",
            "fat": "fat_in_g",
            "omega3": "omega3_in_g",
            "carbs": "carbohydrate_in_g",
            "sugar": "sugar_in_g",
            "fibre": "fibre_in_g",
            "iron": "iron_in_mg",
            "vitc": "vitc_in_mg",
            "magnesium": "magnesium_in_mg",
            "zinc": "zinc_in_mg",
            "vitb12": "vitb12_in_mug",
            "vita": "vita_in_mug",
            "calcium": "calcium_in_mg",
            "vitd": "vitd_in_mug",
            "vitb1": "vitb1_in_mg",
            "vitb2": "vitb2_in_mg",
            "vitb3": "vitb3_in_mg",
            "vitb5": "vitb5_in_mg",
            "vitb6": "vitb6_in_mug",
            "biotin": "biotin_in_mug",
            "iodine": "iodine_in_mug",
            "copper": "copper_in_mug",
            "manganese": "manganese_in_mug",
            "molybdenum": "molybdenum_in_mug",
            "kcal": "energy_in_kcal",
        }

        if self.visible_nutrients:
            self.visible_nutrients = [
                migration_map.get(n, n) for n in self.visible_nutrients
            ]

        if self.thresholds:
            new_thresholds = {}
            for k, v in self.thresholds.items():
                new_key = migration_map.get(k, k)
                new_thresholds[new_key] = v
            self.thresholds = new_thresholds

            try:
                jsonschema.validate(instance=self.thresholds, schema=THRESHOLD_SCHEMA)
            except jsonschema.ValidationError as e:
                raise ValidationError(f"Invalid thresholds format: {e.message}")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class MealPlanDay(models.Model):
    name = models.CharField(max_length=255, default="Neuer Tag")
    meal_plan = models.ForeignKey(
        MealPlan, on_delete=models.CASCADE, related_name="days", null=True, blank=True
    )
    creation_date = models.DateTimeField(auto_now_add=True)
    change_date = models.DateTimeField(auto_now=True)
    foods = models.ManyToManyField(
        Food, through="MealPlanFood", related_name="meal_plan_days"
    )
    removed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-creation_date"]

    def __str__(self):
        return self.name


class MealPlanFood(models.Model):
    class MealType(models.TextChoices):
        BREAKFAST = "breakfast", _("Breakfast")
        LUNCH = "lunch", _("Lunch")
        DINNER = "dinner", _("Dinner")

    meal_plan_day = models.ForeignKey(MealPlanDay, on_delete=models.CASCADE)
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    amount_in_g = models.FloatField()
    export_name = models.CharField(max_length=255, blank=True, default="")
    meal_type = models.CharField(
        max_length=20, choices=MealType.choices, default=MealType.BREAKFAST
    )

    class Meta:
        unique_together = ("meal_plan_day", "food", "meal_type")


class SiteSettings(models.Model):
    """Singleton model for site-wide settings, e.g. a custom PDF logo."""

    logo = models.FileField(upload_to="logos/", blank=True, null=True)
    minilogo = models.FileField(
        upload_to="logos/",
        blank=True,
        null=True,
        help_text="Small logo (50×50 px) shown on the top-right of every PDF page except the first.",
    )
    pdf_footer_line_content = models.TextField(
        max_length=500,
        blank=True,
        default="",
        help_text="Text shown as a light-gray left-aligned footer line on each page of the PDF export.",
    )

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class BackgroundJob(models.Model):
    """Tracks the state and result of a background task (PDF export, BLS import, etc.)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_type = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    progress = models.PositiveSmallIntegerField(default=0)
    task_kwargs = models.JSONField(default=dict, blank=True)
    result_file = models.FileField(
        storage=PrivateExportsStorage(), null=True, blank=True
    )
    error_message = models.TextField(blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class FoodAlias(models.Model):
    """Alternative name/synonym for a food item used during search."""

    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name="aliases")
    alias = models.CharField(max_length=255)

    class Meta:
        unique_together = ("food", "alias")
        ordering = ["alias"]
        verbose_name = "Food Alias"
        verbose_name_plural = "Food Aliases"

    def __str__(self):
        return f"{self.alias} → {self.food.name}"

    def clean(self):
        from django.core.exceptions import ValidationError

        self.alias = " ".join(self.alias.split())
        if not self.alias:
            raise ValidationError({"alias": "Alias cannot be blank."})

        if self.food_id is not None:
            food_name = (
                Food.objects.filter(pk=self.food_id)
                .values_list("name", flat=True)
                .first()
            )
            if food_name and self.alias.lower() == food_name.lower():
                raise ValidationError(
                    {"alias": "Alias is identical to the food's own name."}
                )

            qs = FoodAlias.objects.filter(
                food_id=self.food_id, alias__iexact=self.alias
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {
                        "alias": "An alias with this name already exists for this food (case-insensitive match)."
                    }
                )


# ---------------------------------------------------------------------------
# Cache invalidation signals
# ---------------------------------------------------------------------------


@receiver(post_save, sender=FoodAlias)
@receiver(post_delete, sender=FoodAlias)
def invalidate_alias_cache(sender, **kwargs):
    """Clear the alias index cache whenever aliases are added, changed, or removed."""
    cache.delete(ALIAS_CACHE_KEY)
