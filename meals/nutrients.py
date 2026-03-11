from django.utils.translation import gettext_lazy as _

NUTRIENTS = {
    "energy_in_kcal": {
        "label": _("Energy"),
        "unit": "kcal",
        "food_key": "energy_in_kcal_per_100g",
        "precision": 1,
    },
    "protein_in_g": {
        "label": _("Protein"),
        "unit": "g",
        "food_key": "protein_in_g_per_100g",
        "precision": 1,
    },
    "fat_in_g": {
        "label": _("Fat"),
        "unit": "g",
        "food_key": "fat_in_g_per_100g",
        "precision": 1,
    },
    "omega3_in_g": {
        "label": _("n-3"),
        "unit": "g",
        "food_key": "omega3_in_g_per_100g",
        "precision": 2,
    },
    "carbohydrate_in_g": {
        "label": _("Carbs"),
        "unit": "g",
        "food_key": "carbohydrate_in_g_per_100g",
        "precision": 1,
    },
    "sugar_in_g": {
        "label": _("Sugar"),
        "unit": "g",
        "food_key": "sugar_in_g_per_100g",
        "precision": 1,
    },
    "fibre_in_g": {
        "label": _("Fiber"),
        "unit": "g",
        "food_key": "fibre_in_g_per_100g",
        "precision": 1,
    },
    "iron_in_mg": {
        "label": _("Iron"),
        "unit": "mg",
        "food_key": "iron_in_mg_per_100g",
        "precision": 1,
    },
    "vitc_in_mg": {
        "label": _("Vit. C"),
        "unit": "mg",
        "food_key": "vitc_in_mg_per_100g",
        "precision": 1,
    },
    "magnesium_in_mg": {
        "label": _("Mg"),
        "unit": "mg",
        "food_key": "magnesium_in_mg_per_100g",
        "precision": 1,
    },
    "zinc_in_mg": {
        "label": _("Zinc"),
        "unit": "mg",
        "food_key": "zinc_in_mg_per_100g",
        "precision": 1,
    },
    "vitb12_in_mug": {
        "label": _("Vit. B12"),
        "unit": "µg",
        "food_key": "vitb12_in_mug_per_100g",
        "precision": 2,
    },
    "vita_in_mug": {
        "label": _("Vit. A"),
        "unit": "µg",
        "food_key": "vita_in_mug_per_100g",
        "precision": 1,
    },
    "calcium_in_mg": {
        "label": _("Ca"),
        "unit": "mg",
        "food_key": "calcium_in_mg_per_100g",
        "precision": 1,
    },
    "vitd_in_mug": {
        "label": _("Vit. D"),
        "unit": "µg",
        "food_key": "vitd_in_mug_per_100g",
        "precision": 2,
    },
    "vitb1_in_mg": {
        "label": _("Vit. B1"),
        "unit": "mg",
        "food_key": "vitb1_in_mg_per_100g",
        "precision": 2,
    },
    "vitb2_in_mg": {
        "label": _("Vit. B2"),
        "unit": "mg",
        "food_key": "vitb2_in_mg_per_100g",
        "precision": 2,
    },
    "vitb3_in_mg": {
        "label": _("Vit. B3"),
        "unit": "mg",
        "food_key": "vitb3_in_mg_per_100g",
        "precision": 2,
    },
    "vitb5_in_mg": {
        "label": _("Vit. B5"),
        "unit": "mg",
        "food_key": "vitb5_in_mg_per_100g",
        "precision": 2,
    },
    "vitb6_in_mug": {
        "label": _("Vit. B6"),
        "unit": "µg",
        "food_key": "vitb6_in_mug_per_100g",
        "precision": 1,
    },
    "biotin_in_mug": {
        "label": _("Biotin"),
        "unit": "µg",
        "food_key": "biotin_in_mug_per_100g",
        "precision": 1,
    },
    "iodine_in_mug": {
        "label": _("Iodine"),
        "unit": "µg",
        "food_key": "iodine_in_mug_per_100g",
        "precision": 1,
    },
    "copper_in_mug": {
        "label": _("Copper"),
        "unit": "µg",
        "food_key": "copper_in_mug_per_100g",
        "precision": 1,
    },
    "manganese_in_mug": {
        "label": _("Manganese"),
        "unit": "µg",
        "food_key": "manganese_in_mug_per_100g",
        "precision": 1,
    },
    "molybdenum_in_mug": {
        "label": _("Molybdenum"),
        "unit": "µg",
        "food_key": "molybdenum_in_mug_per_100g",
        "precision": 1,
    },
}

NUTRIENT_IDS = list(NUTRIENTS.keys())

THRESHOLD_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "patternProperties": {
        f"^({'|'.join(NUTRIENT_IDS)})$": {
            "type": "object",
            "properties": {
                "min": {"type": ["number", "null"]},
                "max": {"type": ["number", "null"]},
            },
            "additionalProperties": False,
        }
    },
}
