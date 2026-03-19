# Design: Add Water Nutrient

**Date:** 2026-03-19

## Overview

Add water (`water_in_g_per_100g`) as a tracked nutrient to the RSOS Meal Planner, following the established pattern for all other nutrients.

## Data Model Changes

- **`Food` model**: add `water_in_g_per_100g = FloatField(default=0.0)`
- **`NUTRIENTS` dict** (`nutrients.py`): add `water_in_g` entry after `energy_in_kcal`
  - label: "Water", unit: `g`, food_key: `water_in_g_per_100g`, precision: `1`
- **`ThresholdPreset` model**: add `water_in_g_min` / `water_in_g_max` FloatFields (nullable, blank)
- **Migration**: one migration covering all three model changes

## Serializer & API

- Add `water_in_g_per_100g` to `FoodSerializer.fields`
- No view-level changes needed (nutrient list is data-driven)

## Food Import

- Map BLS column J → `water_in_g_per_100g` in `import_foods.py`

## Frontend

- **Food editor**: data-driven from `nutrients_json` — water auto-appears in the macronutrients group (no template changes, Vue component groups by category)
- **Meal plan detail**: same data-driven pattern — water appears in nutrient columns when visible

## Tests

- Add `water_in_g_per_100g` field to `food_fixtures.json` seed data
- Update import tests to verify BLS column J is read for water
- Update tests asserting the full nutrient field list to include water
