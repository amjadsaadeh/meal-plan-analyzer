# Add Water Nutrient Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `water_in_g_per_100g` as a tracked nutrient (positioned after `energy_in_kcal` in the NUTRIENTS dict), importable from BLS column J, and visible throughout the app.

**Architecture:** Follow the established nutrient-addition pattern: model field → NUTRIENTS dict → serializer → migration → import command → tests. The food editor and meal plan detail Vue components are fully data-driven from `nutrients_json` so require no template or component changes. `water_in_g_per_100g` is not in the food editor's `energyKeys`/`vitaminKeys`/`mineralKeys` sets, so it automatically falls into the Macronutrients group.

**Tech Stack:** Django 6.0, Django REST Framework, openpyxl (BLS import), pytest, Vue 3 (no changes needed)

---

### Task 1: Update nutrients.py — add `water_in_g` entry

**Files:**
- Modify: `meals/nutrients.py`
- Test: `tests/test_nutrients.py`

**Step 1: Write the failing test**

In `tests/test_nutrients.py`, update `EXPECTED_NUTRIENT_KEYS` to insert `"water_in_g"` as the **second** element (after `"energy_in_kcal"`), and update the two count assertions from `25` → `26`:

```python
EXPECTED_NUTRIENT_KEYS = [
    "energy_in_kcal",
    "water_in_g",        # ← insert here
    "protein_in_g",
    "fat_in_g",
    # ... rest unchanged
    "molybdenum_in_mug",
]

# Update both count assertions:
def test_count_is_26(self):          # rename from test_count_is_25
    assert len(NUTRIENTS) == 26

def test_nutrient_ids_length(self):
    assert len(NUTRIENT_IDS) == 26   # was 25
```

**Step 2: Run test to verify it fails**

```bash
cd /home/orchid/projects/meal-plan-analyzer-opencode
uv run pytest tests/test_nutrients.py -v 2>&1 | tail -20
```

Expected: FAIL — `test_no_unexpected_keys`, `test_count_is_26`, `test_nutrient_ids_length` all fail.

**Step 3: Add water to NUTRIENTS dict**

In `meals/nutrients.py`, insert after the `energy_in_kcal` entry:

```python
NUTRIENTS = {
    "energy_in_kcal": {
        "label": _("Energy"),
        "unit": "kcal",
        "food_key": "energy_in_kcal_per_100g",
        "precision": 1,
    },
    "water_in_g": {                          # ← add this block
        "label": _("Water"),
        "unit": "g",
        "food_key": "water_in_g_per_100g",
        "precision": 1,
    },
    "protein_in_g": {
        # ... unchanged
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_nutrients.py -v 2>&1 | tail -20
```

Expected: the nutrients tests PASS (note: `test_food_keys_map_to_food_model_fields` will still fail until the model field exists — that's expected).

**Step 5: Commit**

```bash
uv run black meals/nutrients.py tests/test_nutrients.py
git add meals/nutrients.py tests/test_nutrients.py
git commit -m "feat: add water_in_g nutrient entry to NUTRIENTS dict"
```

---

### Task 2: Add `water_in_g_per_100g` field to Food model and ThresholdPreset

**Files:**
- Modify: `meals/models.py`
- Create: `meals/migrations/0027_food_water_in_g_per_100g.py` (auto-generated)

**Step 1: Write the failing test**

In `tests/test_nutrients.py`, `test_food_keys_map_to_food_model_fields` currently fails because `water_in_g_per_100g` doesn't exist on `Food`. Verify this is failing:

```bash
uv run pytest tests/test_nutrients.py::TestNutrientsDict::test_food_keys_map_to_food_model_fields -v
```

Expected: FAIL — `food_key 'water_in_g_per_100g' not found on Food model`.

**Step 2: Add field to Food model**

In `meals/models.py`, in the `Food` class, add after `energy_in_kcal_per_100g`:

```python
energy_in_kcal_per_100g = models.FloatField()
water_in_g_per_100g = models.FloatField(default=0.0)   # ← add this line
protein_in_g_per_100g = models.FloatField(default=0.0)
```

**Step 3: Add fields to ThresholdPreset**

In `meals/models.py`, in the `ThresholdPreset` class, add after `energy_in_kcal_max`:

```python
energy_in_kcal_max = models.FloatField(null=True, blank=True)

water_in_g_min = models.FloatField(null=True, blank=True)    # ← add
water_in_g_max = models.FloatField(null=True, blank=True)    # ← add

protein_in_g_min = models.FloatField(null=True, blank=True)
```

**Step 4: Create migration**

```bash
uv run python manage.py makemigrations meals --name food_water_in_g_per_100g
```

Expected output: `Migrations for 'meals': meals/migrations/0027_food_water_in_g_per_100g.py`

**Step 5: Apply migration**

```bash
uv run python manage.py migrate
```

**Step 6: Run test to verify it now passes**

```bash
uv run pytest tests/test_nutrients.py -v 2>&1 | tail -10
```

Expected: ALL PASS.

**Step 7: Commit**

```bash
uv run black meals/models.py
git add meals/models.py meals/migrations/0027_food_water_in_g_per_100g.py
git commit -m "feat: add water_in_g_per_100g field to Food and ThresholdPreset models"
```

---

### Task 3: Update FoodSerializer to expose the water field

**Files:**
- Modify: `meals/serializers.py`
- Test: `tests/api/test_foods.py`

**Step 1: Write the failing test**

In `tests/api/test_foods.py`, find any test that lists/creates a food and checks response fields. Add a check for `water_in_g_per_100g`. If no such test exists, add one:

```python
@pytest.mark.django_db
def test_food_response_includes_water_field(authenticated_client):
    response = authenticated_client.get("/api/foods/")
    assert response.status_code == 200
    # The fixture foods are loaded; grab first result
    data = response.json()
    foods = data.get("results", data)
    assert len(foods) > 0
    assert "water_in_g_per_100g" in foods[0], (
        "water_in_g_per_100g field missing from food API response"
    )
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/api/test_foods.py::test_food_response_includes_water_field -v
```

Expected: FAIL — field not in response.

**Step 3: Add field to FoodSerializer**

In `meals/serializers.py`, in `FoodSerializer.Meta.fields`, add `"water_in_g_per_100g"` after `"energy_in_kcal_per_100g"`:

```python
fields = [
    "id",
    "bls_code",
    "name",
    "energy_in_kj_per_100g",
    "energy_in_kcal_per_100g",
    "water_in_g_per_100g",         # ← add here
    "protein_in_g_per_100g",
    # ... rest unchanged
]
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/api/test_foods.py::test_food_response_includes_water_field -v
```

Expected: PASS.

**Step 5: Commit**

```bash
uv run black meals/serializers.py tests/api/test_foods.py
git add meals/serializers.py tests/api/test_foods.py
git commit -m "feat: expose water_in_g_per_100g in FoodSerializer"
```

---

### Task 4: Update import command to read column J for water

**Files:**
- Modify: `meals/management/commands/import_foods.py`
- Modify: `tests/generate_test_data.py`
- Test: `tests/test_food_import.py`

**Step 1: Write the failing test**

In `tests/test_food_import.py`, add a test that verifies column J is read as water:

```python
@pytest.mark.django_db
def test_food_import_reads_water_from_column_j():
    """Column J in the BLS Excel file contains water content."""
    wb = openpyxl.load_workbook(TEST_XLSX, data_only=True)
    ws = wb.active
    first_code = ws["A2"].value
    water_j = ws["J2"].value

    call_command("import_foods", str(TEST_XLSX))

    food = Food.objects.get(bls_code=first_code)
    if water_j is not None:
        assert pytest.approx(food.water_in_g_per_100g, abs=0.01) == float(water_j)
    else:
        assert food.water_in_g_per_100g == 0.0
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_food_import.py::test_food_import_reads_water_from_column_j -v
```

Expected: FAIL — `water_in_g_per_100g` not set from column J (it uses 0.0 default regardless).

**Step 3: Update generate_test_data.py to write column J**

In `tests/generate_test_data.py`, add `"J": "WATER"` to the `cols` dict and write a random value to column J for each row:

```python
cols = {
    "A": "BLS_CODE",
    "B": "NAME",
    "D": "KJ",
    "G": "KCAL",
    "J": "WATER",          # ← add
    "M": "PROTEIN",
    # ... rest unchanged
}

# In the row loop, add:
ws[f"J{row}"] = random.uniform(0, 100)   # WATER
```

**Step 4: Regenerate test data files**

```bash
cd /home/orchid/projects/meal-plan-analyzer-opencode
uv run python tests/generate_test_data.py
```

Then regenerate the zip files:

```python
# Run this as a one-off Python snippet:
import zipfile, shutil
# Daten zip (with "Daten" in filename)
with zipfile.ZipFile("tests/data/test_foods_Daten.zip", "w") as zf:
    zf.write("tests/data/test_foods.xlsx", "test_foods_Daten.xlsx")
# No-daten zip (without "Daten" in filename)
with zipfile.ZipFile("tests/data/test_foods_no_daten.zip", "w") as zf:
    zf.write("tests/data/test_foods.xlsx", "test_foods_other.xlsx")
```

Run it:
```bash
uv run python -c "
import zipfile
with zipfile.ZipFile('tests/data/test_foods_Daten.zip', 'w') as zf:
    zf.write('tests/data/test_foods.xlsx', 'test_foods_Daten.xlsx')
with zipfile.ZipFile('tests/data/test_foods_no_daten.zip', 'w') as zf:
    zf.write('tests/data/test_foods.xlsx', 'test_foods_other.xlsx')
print('Done')
"
```

**Step 5: Update import command to read column J**

In `meals/management/commands/import_foods.py`, add after `IDX_BLS = col_to_idx("A")`:

```python
IDX_BLS = col_to_idx("A")
IDX_NAME = col_to_idx("B")
IDX_KJ = col_to_idx("D")
IDX_KCAL = col_to_idx("G")
IDX_WATER = col_to_idx("J")    # ← add this line
IDX_PROTEIN = col_to_idx("M")
# ... rest unchanged
```

Then add parsing after `energy_kcal = parse_float(row[IDX_KCAL])`:

```python
energy_kcal = parse_float(row[IDX_KCAL])
water = parse_float(row[IDX_WATER])      # ← add this line
protein = parse_float(row[IDX_PROTEIN])
```

Then add to the `Food.objects.update_or_create` defaults dict after `energy_in_kcal_per_100g`:

```python
"energy_in_kcal_per_100g": energy_kcal,
"water_in_g_per_100g": water,           # ← add this line
"protein_in_g_per_100g": protein,
```

**Step 6: Run test to verify it passes**

```bash
uv run pytest tests/test_food_import.py -v 2>&1 | tail -20
```

Expected: ALL PASS including `test_food_import_reads_water_from_column_j`.

**Step 7: Commit**

```bash
uv run black meals/management/commands/import_foods.py tests/generate_test_data.py tests/test_food_import.py
git add meals/management/commands/import_foods.py tests/generate_test_data.py tests/test_food_import.py tests/data/test_foods.xlsx tests/data/test_foods_Daten.zip tests/data/test_foods_no_daten.zip
git commit -m "feat: import water_in_g_per_100g from BLS column J"
```

---

### Task 5: Run full test suite and verify

**Step 1: Format all Python**

```bash
uv run black .
```

**Step 2: Run all non-frontend tests**

```bash
uv run pytest tests/test_*.py tests/api/ --create-db -v 2>&1 | tail -30
```

Expected: ALL PASS.

**Step 3: Fix any remaining failures**

Common issues to watch for:
- Any test that hardcodes `len(NUTRIENT_IDS) == 25` → update to `26`
- Any test that hardcodes the full list of Food fields and doesn't include `water_in_g_per_100g`
- ThresholdPreset tests that enumerate all `_min`/`_max` fields

**Step 4: Final commit (formatting + any fixes)**

```bash
uv run black .
git add -u
git commit -m "test: fix remaining test assertions for water nutrient addition"
```

---

### Task 6: Verify ThresholdPreset migration and admin (smoke check)

**Step 1: Check migration applies cleanly**

```bash
uv run python manage.py migrate --run-syncdb 2>&1
```

Expected: `No migrations to apply.`

**Step 2: Verify ThresholdPreset admin fields (manual check)**

The `ThresholdPresetSerializer` uses `fields = "__all__"` so `water_in_g_min`/`water_in_g_max` are automatically included in the API. No changes needed.

**Step 3: Run API threshold preset tests**

```bash
uv run pytest tests/api/test_threshold_presets.py -v
```

Expected: PASS.

---

### Task 7: Final push-readiness check

**Step 1: Run complete test suite**

```bash
uv run black --check . && uv run pytest tests/test_*.py tests/api/ --create-db 2>&1 | tail -20
```

Expected: formatting OK, all tests PASS.

**Step 2: Summarize changes made**

Files changed:
- `meals/nutrients.py` — `water_in_g` added after `energy_in_kcal`
- `meals/models.py` — `Food.water_in_g_per_100g`, `ThresholdPreset.water_in_g_min/max`
- `meals/migrations/0027_food_water_in_g_per_100g.py` — auto-generated
- `meals/serializers.py` — `water_in_g_per_100g` in `FoodSerializer.fields`
- `meals/management/commands/import_foods.py` — `IDX_WATER = col_to_idx("J")` + defaults
- `tests/generate_test_data.py` — column J written with water values
- `tests/data/test_foods.xlsx`, `test_foods_Daten.zip`, `test_foods_no_daten.zip` — regenerated
- `tests/test_nutrients.py` — `water_in_g` in expected keys, counts updated to 26
- `tests/test_food_import.py` — `test_food_import_reads_water_from_column_j` added
- `tests/api/test_foods.py` — `test_food_response_includes_water_field` added

No frontend Vue component changes needed — data-driven via `nutrients_json`.
