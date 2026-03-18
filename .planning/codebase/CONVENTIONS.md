# Coding Conventions

**Analysis Date:** 2026-03-16

## Naming Patterns

**Files:**
- Snake_case for all Python files: `meal_extras.py`, `test_model_validation.py`, `food_search_semantics.py`
- Test files prefixed `test_`: `test_foods.py`, `test_mealplans.py`
- Templates use `.html.j2` extension: `mealplan_detail.html.j2`, `base.html.j2`
- SCSS entry points named after feature: `mealplan_detail.scss`, `food_editor.scss`
- SCSS partials prefixed with `_`: `_layout.scss`, `_variables.scss`, `_reset.scss`

**Functions:**
- `snake_case` throughout: `get_alias_index()`, `normalize_umlauts()`, `parse_food_search()`, `get_food_ids_by_alias()`
- Private helpers prefixed with `_`: `_umlaut_search_variants()`, `_make_food()` (in tests), `_FoodBrowsePagination`
- Module-level constants in `UPPER_SNAKE_CASE`: `ALIAS_CACHE_KEY`, `NUTRIENTS`, `NUTRIENT_IDS`, `THRESHOLD_SCHEMA`, `_UMLAUT_PAIRS`

**Variables:**
- `snake_case` throughout: `search_query`, `clean_search`, `name_food_ids`, `low_energy_intent`
- Queryset variables named `queryset` or `<entity>_queryset`: `name_queryset`
- Boolean variables use descriptive names: `low_energy_intent`, `high_energy_intent`

**Types/Classes:**
- PascalCase for all classes: `FoodViewSet`, `MealPlanSerializer`, `MealPlanDayFactory`
- Inner choice classes as nested `TextChoices`: `class MealType(models.TextChoices)`
- Factory classes suffixed `Factory`: `FoodFactory`, `MealPlanFactory`, `MealPlanDayFactory`

**Model fields:**
- Nutrient fields encode unit and quantity in name: `energy_in_kcal_per_100g`, `protein_in_g_per_100g`, `vitb12_in_mug_per_100g`
- Nutrient keys (in `NUTRIENTS`) strip the `_per_100g` suffix: `energy_in_kcal`, `protein_in_g`, `vitb12_in_mug`
- Threshold preset fields pair as `<nutrient_key>_min` / `<nutrient_key>_max`: `energy_in_kcal_min`, `energy_in_kcal_max`

**URL names:**
- Kebab-case: `meal-plan-list`, `meal-plan-detail`, `meal-plan-pdf`, `food-editor`

## Code Style

**Formatter:**
- `black` with `line-length = 88`, `target-version = ["py312"]`
- Configured in `pyproject.toml` under `[tool.black]`
- Enforced in CI via `uv run black --check .`
- Run locally: `uv run black .`

**Linting:**
- No separate linter configured (no flake8, ruff, or pylint config detected)
- Black handles formatting; no style linter beyond it

## Import Organization

**Order (observed pattern):**
1. Standard library: `import re`, `import os`, `import json`, `import secrets`
2. Django: `from django.db import models`, `from django.shortcuts import render`
3. Third-party: `from rest_framework import viewsets`, `import jsonschema`
4. Local app imports: `from .models import Food`, `from .nutrients import NUTRIENTS`
5. Test-specific: `import pytest` first in test files, then Django/DRF, then app imports

**Path Aliases:**
- None; all imports use explicit module paths

**Deferred imports (used in a few places):**
- Some imports inside functions for circular dependency avoidance: `from django.shortcuts import redirect` inside `meal_plan_detail()`, `from django.core.exceptions import ValidationError as DjangoValidationError` inside `MealPlanSerializer.validate()`
- This pattern is acceptable but not the norm; prefer top-level imports when safe

## Error Handling

**Django model errors:**
- Models raise `django.core.exceptions.ValidationError` on `clean()` / `full_clean()`
- `MealPlan.save()` always calls `full_clean()` — model validation always runs on save
- Do not bypass with `.update()` when threshold/nutrient integrity matters

**DRF serializer errors:**
- `FoodSerializer.validate()` raises `serializers.ValidationError` with field-specific dict: `{"energy_in_kcal_per_100g": "Must be 0 or greater."}`
- `MealPlanSerializer.validate()` catches `DjangoValidationError` and re-raises as `serializers.ValidationError` to return 400 instead of 500

**Template filters:**
- Catch `(ValueError, TypeError)` and return a safe fallback (usually `0` or `[]`):
  ```python
  def divide_by_100_mult(value, arg):
      try:
          return (float(value) / 100) * float(arg)
      except (ValueError, TypeError):
          return 0
  ```

**Views:**
- Use `get_object_or_404()` for all object lookups in template views
- DRF viewsets use standard DRF exception handling; no custom exception handlers detected

## Logging

**Framework:** Not configured; no logging calls found in application code.

## Comments

**When to Comment:**
- Module-level docstrings on test files describing what they cover (see `tests/test_model_validation.py`, `tests/test_template_filters.py`)
- Class-level docstrings on test classes describing the scenario
- Inline comments with `# ------` section dividers to group related tests or code blocks
- Docstrings on non-obvious utility functions: `get_alias_index()`, `_umlaut_search_variants()`
- Inline comments explaining algorithm strategy within complex functions (see `_umlaut_search_variants()`)

**Examples:**
```python
def get_alias_index():
    """Return a cached dict mapping food_id → list[alias_string].

    The index is built from FoodAlias rows on the first call and then stored
    in Django's cache backend for up to one hour to keep database load low.
    Cache-invalidation signals (see bottom of file) clear the entry whenever
    any FoodAlias row is created, changed, or deleted.
    """
```

## Function Design

**Size:** Helper functions are small and focused; `FoodViewSet.list()` and `meal_plan_detail()` are longer but contain logically grouped blocks separated by inline comments.

**Parameters:** Prefer keyword arguments for `Food.objects.create(**defaults)`. Factory defaults use `defaults.update(kwargs)` pattern:
```python
def _make_food(**kwargs):
    defaults = dict(bls_code="TEST001", name="Testfood", ...)
    defaults.update(kwargs)
    return Food.objects.create(**defaults)
```

**Return Values:** Functions return single-type values; utility functions either return the computed value or a safe default on error.

## Module Design

**Exports:**
- No `__all__` declarations; modules export everything at module level
- Public API of models module is consumed via direct imports from `meals.models`

**Barrel Files:**
- Not used; imports are always explicit

## i18n

**Strings:**
- User-visible strings in models use `gettext_lazy`: `from django.utils.translation import gettext_lazy as _`
- User-visible strings in views use `gettext` (evaluated at request time): `from django.utils.translation import gettext as _`
- Default names are German: `"Neuer Plan"`, `"Neuer Tag"` — translated via `_()` in views at request time
- Nutrient labels in `meals/nutrients.py` use `_()` from `gettext_lazy`

## Key Domain Rules (Enforce in All New Code)

- **Soft deletes only for `MealPlanDay`**: set `removed=True`, never `.delete()`. Always filter with `removed=False`.
- **Nutrient keys**: use exact strings from `NUTRIENT_IDS` (e.g. `"protein_in_g"` not `"protein"`).
- **Alias cache**: never call `FoodAlias.objects.filter(...)` in hot paths; use `get_alias_index()` from `meals.models`.
- **SiteSettings singleton**: always access via `SiteSettings.get()`, never `SiteSettings.objects.get(pk=1)`.
- **Energy sync**: when creating/updating a food via the API, supply either `energy_in_kcal_per_100g` or `energy_in_kj_per_100g`, not both.

---

*Convention analysis: 2026-03-16*
