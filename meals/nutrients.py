NUTRIENTS = {
    'energy_in_kcal': {
        'label': 'Energie',
        'unit': 'kcal',
        'food_key': 'energy_in_kcal_per_100g',
        'precision': 1
    },
    'protein_in_g': {
        'label': 'Protein',
        'unit': 'g',
        'food_key': 'protein_in_g_per_100g',
        'precision': 1
    },
    'fat_in_g': {
        'label': 'Fett',
        'unit': 'g',
        'food_key': 'fat_in_g_per_100g',
        'precision': 1
    },
    'omega3_in_g': {
        'label': 'Omega-3',
        'unit': 'g',
        'food_key': 'omega3_in_g_per_100g',
        'precision': 2
    },
    'carbohydrate_in_g': {
        'label': 'Kohlenhydrate',
        'unit': 'g',
        'food_key': 'carbohydrate_in_g_per_100g',
        'precision': 1
    },
    'sugar_in_g': {
        'label': 'Zucker',
        'unit': 'g',
        'food_key': 'sugar_in_g_per_100g',
        'precision': 1
    },
    'fibre_in_g': {
        'label': 'Ballaststoffe',
        'unit': 'g',
        'food_key': 'fibre_in_g_per_100g',
        'precision': 1
    },
    'iron_in_mg': {
        'label': 'Eisen',
        'unit': 'mg',
        'food_key': 'iron_in_mg_per_100g',
        'precision': 1
    },
    'vitc_in_mg': {
        'label': 'Vit C',
        'unit': 'mg',
        'food_key': 'vitc_in_mg_per_100g',
        'precision': 1
    },
    'magnesium_in_mg': {
        'label': 'Magnesium',
        'unit': 'mg',
        'food_key': 'magnesium_in_mg_per_100g',
        'precision': 1
    },
    'zinc_in_mg': {
        'label': 'Zink',
        'unit': 'mg',
        'food_key': 'zinc_in_mg_per_100g',
        'precision': 1
    },
    'vitb12_in_mug': {
        'label': 'Vit B12',
        'unit': 'µg',
        'food_key': 'vitb12_in_mug_per_100g',
        'precision': 2
    },
    'vita_in_mug': {
        'label': 'Vit A',
        'unit': 'µg',
        'food_key': 'vita_in_mug_per_100g',
        'precision': 1
    },
    'calcium_in_mg': {
        'label': 'Calcium',
        'unit': 'mg',
        'food_key': 'calcium_in_mg_per_100g',
        'precision': 1
    },
    'vitd_in_mug': {
        'label': 'Vit D',
        'unit': 'µg',
        'food_key': 'vitd_in_mug_per_100g',
        'precision': 2
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
                "max": {"type": ["number", "null"]}
            },
            "additionalProperties": False
        }
    }
}
