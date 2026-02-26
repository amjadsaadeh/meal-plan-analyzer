"""
Tests for meals/nutrients.py — the NUTRIENTS dict, NUTRIENT_IDS list,
and THRESHOLD_SCHEMA.

Verifies:
  - All 15 expected nutrients are present
  - Every entry has required keys: label, unit, food_key, precision
  - food_key values map to actual Food model fields
  - NUTRIENT_IDS exactly matches the keys of NUTRIENTS in the same order
  - THRESHOLD_SCHEMA patternProperties covers every nutrient in NUTRIENT_IDS
"""

import pytest
from meals.nutrients import NUTRIENTS, NUTRIENT_IDS, THRESHOLD_SCHEMA
from meals.models import Food


EXPECTED_NUTRIENT_KEYS = [
    'energy_in_kcal',
    'protein_in_g',
    'fat_in_g',
    'omega3_in_g',
    'carbohydrate_in_g',
    'sugar_in_g',
    'fibre_in_g',
    'iron_in_mg',
    'vitc_in_mg',
    'magnesium_in_mg',
    'zinc_in_mg',
    'vitb12_in_mug',
    'vita_in_mug',
    'calcium_in_mg',
    'vitd_in_mug',
    'vitb1_in_mg',
    'vitb2_in_mg',
    'vitb3_in_mg',
    'vitb5_in_mg',
    'vitb6_in_mug',
    'biotin_in_mug',
    'iodine_in_mug',
    'copper_in_mug',
    'manganese_in_mug',
]


class TestNutrientsDict:
    def test_all_expected_keys_present(self):
        for key in EXPECTED_NUTRIENT_KEYS:
            assert key in NUTRIENTS, f"Missing nutrient key: {key}"

    def test_no_unexpected_keys(self):
        assert set(NUTRIENTS.keys()) == set(EXPECTED_NUTRIENT_KEYS)

    def test_count_is_24(self):
        assert len(NUTRIENTS) == 24

    def test_every_entry_has_required_fields(self):
        required = {'label', 'unit', 'food_key', 'precision'}
        for key, data in NUTRIENTS.items():
            missing = required - set(data.keys())
            assert not missing, f"Nutrient '{key}' missing fields: {missing}"

    def test_labels_are_non_empty_strings(self):
        for key, data in NUTRIENTS.items():
            label_str = str(data['label'])
            assert label_str, f"Nutrient '{key}' has empty label"

    def test_units_are_non_empty_strings(self):
        for key, data in NUTRIENTS.items():
            assert isinstance(data['unit'], str) and data['unit'], \
                f"Nutrient '{key}' has empty unit"

    def test_precision_is_positive_int_or_zero(self):
        for key, data in NUTRIENTS.items():
            assert isinstance(data['precision'], int) and data['precision'] >= 0, \
                f"Nutrient '{key}' has invalid precision: {data['precision']}"

    def test_food_keys_map_to_food_model_fields(self):
        """Every food_key in NUTRIENTS must be a real field on the Food model."""
        food_field_names = {f.name for f in Food._meta.get_fields()}
        for key, data in NUTRIENTS.items():
            assert data['food_key'] in food_field_names, \
                f"Nutrient '{key}' has food_key '{data['food_key']}' not found on Food model"


class TestNutrientIDs:
    def test_nutrient_ids_matches_nutrients_keys(self):
        assert NUTRIENT_IDS == list(NUTRIENTS.keys())

    def test_nutrient_ids_length(self):
        assert len(NUTRIENT_IDS) == 24

    def test_nutrient_ids_contains_all_expected(self):
        for key in EXPECTED_NUTRIENT_KEYS:
            assert key in NUTRIENT_IDS

    def test_nutrient_ids_no_duplicates(self):
        assert len(NUTRIENT_IDS) == len(set(NUTRIENT_IDS))


class TestThresholdSchema:
    def test_schema_is_dict(self):
        assert isinstance(THRESHOLD_SCHEMA, dict)

    def test_schema_type_is_object(self):
        assert THRESHOLD_SCHEMA.get('type') == 'object'

    def test_schema_disallows_additional_properties(self):
        assert THRESHOLD_SCHEMA.get('additionalProperties') is False

    def test_pattern_properties_covers_all_nutrient_ids(self):
        """The patternProperties regex must match every key in NUTRIENT_IDS."""
        import re
        pattern_keys = list(THRESHOLD_SCHEMA.get('patternProperties', {}).keys())
        assert len(pattern_keys) == 1, "Expected exactly one patternProperty regex"
        pattern = pattern_keys[0]
        for nutrient_id in NUTRIENT_IDS:
            assert re.match(pattern, nutrient_id), \
                f"Schema pattern '{pattern}' does not match nutrient ID '{nutrient_id}'"

    def test_each_threshold_entry_allows_min_and_max(self):
        """The schema for each threshold entry must declare min and max properties."""
        for _, entry_schema in THRESHOLD_SCHEMA['patternProperties'].items():
            props = entry_schema.get('properties', {})
            assert 'min' in props, "Threshold schema entry is missing 'min'"
            assert 'max' in props, "Threshold schema entry is missing 'max'"

    def test_min_max_accept_number_or_null(self):
        """min and max should each accept number or null types."""
        for _, entry_schema in THRESHOLD_SCHEMA['patternProperties'].items():
            for field in ('min', 'max'):
                allowed_types = entry_schema['properties'][field].get('type', [])
                assert 'number' in allowed_types, f"'{field}' does not allow 'number'"
                assert 'null' in allowed_types, f"'{field}' does not allow 'null'"
