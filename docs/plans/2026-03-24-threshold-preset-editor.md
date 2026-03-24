# Threshold Preset Editor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Threshold Preset section (list + editor) accessible from the top nav bar, with search, expand/collapse nutrient rows, and auto-saving editor.

**Architecture:** Two Vue 3 SPAs — `threshold-preset-list` and `threshold-preset-editor` — mirroring the food-database + food-editor pattern. Both connect to the existing `/api/threshold-presets/` DRF endpoint. Each SPA gets a Django view, URL, and template. One shared SCSS file covers both pages.

**Tech Stack:** Django 6.0, Vue 3 (Composition API, no build-time dependencies beyond what exists), Vite 5, DRF, SCSS (libsass). Package manager: `uv` (Python), `pnpm` (JS). Formatter: `black`.

---

## Reference: Key Existing Files

Before starting, read these files to understand patterns to mirror:
- `meals/views.py` lines 919–972 — `food_database` and `food_editor` view functions
- `meals/urls.py` — URL registration pattern
- `meals/templates/meals/food_database.html.j2` — template pattern
- `meals/templates/meals/base.html.j2` lines 21–29 — nav link pattern
- `frontend/src/food-database/components/FoodDatabaseApp.vue` — root SPA component pattern
- `frontend/src/food-database/components/FoodRow.vue` — `highlightMatch` function to reuse
- `frontend/src/food-database/main.js` — entry point pattern
- `vite.config.js` — where to add new entry points
- `meals/static/meals/scss/food_database.scss` — SCSS to mirror
- `meals/static/meals/scss/_variables.scss` — design tokens
- `meals/models.py` lines 71–156 — `ThresholdPreset` model fields
- `meals/nutrients.py` — `NUTRIENTS` ordered dict (keys map directly to `{key}_min`/`{key}_max` on `ThresholdPreset`)

## Key Mapping

NUTRIENTS key → ThresholdPreset API field names:
- `energy_in_kcal` → `energy_in_kcal_min` / `energy_in_kcal_max`
- `water_in_g` → `water_in_g_min` / `water_in_g_max`
- (pattern: `{key}_min` / `{key}_max` for every key in NUTRIENTS)

Default nutrients (always visible): `energy_in_kcal`, `water_in_g`, `carbohydrate_in_g`, `fat_in_g`, `protein_in_g`

---

## Task 1: Django views, URLs, templates

**Files:**
- Modify: `meals/views.py` (add two views near line 919)
- Modify: `meals/urls.py` (add two URL patterns)
- Create: `meals/templates/meals/threshold_preset_list.html.j2`
- Create: `meals/templates/meals/threshold_preset_editor.html.j2`
- Test: `tests/test_threshold_preset_views.py`

### Step 1: Write the failing tests

Create `tests/test_threshold_preset_views.py`:

```python
"""Tests for the threshold preset list and editor Django views."""

import pytest
from django.urls import reverse
from meals.models import ThresholdPreset

pytestmark = pytest.mark.django_db


def test_list_redirects_unauthenticated(api_client):
    response = api_client.get("/threshold-presets/")
    assert response.status_code == 302
    assert "login" in response.url


def test_list_renders_ok(authenticated_client):
    response = authenticated_client.get("/threshold-presets/")
    assert response.status_code == 200


def test_list_has_mount_element(authenticated_client):
    response = authenticated_client.get("/threshold-presets/")
    assert b'id="threshold-preset-list-app"' in response.content


def test_list_passes_nutrients_json(authenticated_client):
    response = authenticated_client.get("/threshold-presets/")
    assert b"energy_in_kcal" in response.content


def test_editor_redirects_unauthenticated(api_client):
    preset = ThresholdPreset.objects.create(name="Test")
    response = api_client.get(f"/threshold-presets/{preset.id}/")
    assert response.status_code == 302
    assert "login" in response.url


def test_editor_renders_ok(authenticated_client):
    preset = ThresholdPreset.objects.create(name="Test")
    response = authenticated_client.get(f"/threshold-presets/{preset.id}/")
    assert response.status_code == 200


def test_editor_returns_404_for_missing(authenticated_client):
    response = authenticated_client.get("/threshold-presets/9999/")
    assert response.status_code == 404


def test_editor_has_mount_element(authenticated_client):
    preset = ThresholdPreset.objects.create(name="Test")
    response = authenticated_client.get(f"/threshold-presets/{preset.id}/")
    assert b'id="threshold-preset-editor-app"' in response.content


def test_editor_passes_preset_id(authenticated_client):
    preset = ThresholdPreset.objects.create(name="Test")
    response = authenticated_client.get(f"/threshold-presets/{preset.id}/")
    assert str(preset.id).encode() in response.content


def test_nav_link_present(authenticated_client):
    response = authenticated_client.get("/threshold-presets/")
    assert b"/threshold-presets/" in response.content
```

### Step 2: Run tests to verify they fail

```bash
uv run black . && uv run pytest tests/test_threshold_preset_views.py -v
```

Expected: all tests FAIL (no view or URL exists yet).

### Step 3: Add the two views to `meals/views.py`

Add after the `food_editor` function (after line 972). You need `json` (already imported), `reverse` (already imported), `get_object_or_404` (add to imports if missing — check line ~1 of views.py for existing imports), `ThresholdPreset` (already imported), `NUTRIENTS` (already imported), and the `_` translation function (already imported).

Add to the imports at the top of `meals/views.py` if `get_object_or_404` is not already there:
```python
from django.shortcuts import render, redirect, get_object_or_404
```
(Check first — it may already be imported. Add only if missing.)

Add these two functions at the end of `meals/views.py`:

```python
@login_required
def threshold_preset_list(request):
    nutrients_list = [
        {"key": key, "label": str(meta["label"]), "unit": meta["unit"]}
        for key, meta in NUTRIENTS.items()
    ]
    i18n = {
        "searchPlaceholder": _("Search presets\u2026"),
        "createPreset": _("Create Preset"),
        "noData": _("No threshold presets found."),
        "colName": _("Name"),
        "networkError": _("Network error"),
        "newPresetName": _("New Preset"),
        "errorCreate": _("Error creating preset"),
        "showMore": _("Show more nutrients"),
        "showLess": _("Show less"),
    }
    return render(
        request,
        "meals/threshold_preset_list.html.j2",
        {
            "nutrients_json": json.dumps(nutrients_list),
            "i18n_json": json.dumps({k: str(v) for k, v in i18n.items()}),
            "preset_editor_base_url": reverse("threshold-preset-list").rstrip("/")
            + "/",
        },
    )


@login_required
def threshold_preset_editor(request, pk):
    get_object_or_404(ThresholdPreset, pk=pk)
    nutrients_list = [
        {"key": key, "label": str(meta["label"]), "unit": meta["unit"]}
        for key, meta in NUTRIENTS.items()
    ]
    i18n = {
        "saved": _("Saved"),
        "saving": _("Saving\u2026"),
        "errorSaving": _("Error saving"),
        "backToList": _("Threshold Presets"),
        "min": _("Min"),
        "max": _("Max"),
        "deletePreset": _("Delete preset"),
        "deleteConfirm": _("Delete this preset?"),
        "networkError": _("Network error"),
        "showMore": _("Show more nutrients"),
        "showLess": _("Show less"),
        "notFound": _("Preset not found."),
    }
    return render(
        request,
        "meals/threshold_preset_editor.html.j2",
        {
            "preset_id": pk,
            "nutrients_json": json.dumps(nutrients_list),
            "i18n_json": json.dumps({k: str(v) for k, v in i18n.items()}),
            "preset_list_url": reverse("threshold-preset-list"),
        },
    )
```

Note: the `preset_editor_base_url` is `/threshold-presets/` — the list view uses `reverse("threshold-preset-list")` which returns `/threshold-presets/`. That string is already the correct base URL for the editor.

### Step 4: Register the views in `meals/urls.py`

Add the imports at the top:
```python
from .views import (
    ...
    threshold_preset_list,
    threshold_preset_editor,
)
```

Add the URL patterns (after the `foods/<int:pk>/` line):
```python
path("threshold-presets/", threshold_preset_list, name="threshold-preset-list"),
path("threshold-presets/<int:pk>/", threshold_preset_editor, name="threshold-preset-editor"),
```

### Step 5: Create `meals/templates/meals/threshold_preset_list.html.j2`

```django
{% extends 'meals/base.html.j2' %}
{% load static i18n sass_tags %}

{% block title %}{% trans "Threshold Presets" %} | Meal Plan Analyzer{% endblock %}

{% block extra_css %}
    <link rel="stylesheet" href="{% sass_src 'meals/scss/threshold_preset.scss' %}">
{% endblock %}

{% block content %}
<div class="container" style="max-width: 960px;">
    <div
        id="threshold-preset-list-app"
        data-csrf-token="{{ csrf_token }}"
        data-preset-editor-base-url="{{ preset_editor_base_url }}"
        data-nutrients='{{ nutrients_json }}'
        data-i18n='{{ i18n_json }}'
    ></div>
</div>
{% endblock %}

{% block extra_js %}
{% load django_vite %}
{% vite_asset 'frontend/src/threshold-preset-list/main.js' %}
{% endblock %}
```

### Step 6: Create `meals/templates/meals/threshold_preset_editor.html.j2`

```django
{% extends 'meals/base.html.j2' %}
{% load static i18n sass_tags %}

{% block title %}{% trans "Threshold Preset Editor" %} | Meal Plan Analyzer{% endblock %}

{% block extra_css %}
    <link rel="stylesheet" href="{% sass_src 'meals/scss/threshold_preset.scss' %}">
{% endblock %}

{% block content %}
<div class="container" style="max-width: 720px;">
    <div
        id="threshold-preset-editor-app"
        data-preset-id="{{ preset_id }}"
        data-csrf-token="{{ csrf_token }}"
        data-nutrients='{{ nutrients_json }}'
        data-i18n='{{ i18n_json }}'
        data-preset-list-url="{{ preset_list_url }}"
    ></div>
</div>
{% endblock %}

{% block extra_js %}
{% load django_vite %}
{% vite_asset 'frontend/src/threshold-preset-editor/main.js' %}
{% endblock %}
```

### Step 7: Run tests to verify they pass

```bash
uv run black . && uv run pytest tests/test_threshold_preset_views.py -v
```

Expected: all 10 tests PASS.

### Step 8: Commit

```bash
git add meals/views.py meals/urls.py \
    meals/templates/meals/threshold_preset_list.html.j2 \
    meals/templates/meals/threshold_preset_editor.html.j2 \
    tests/test_threshold_preset_views.py
git commit -m "feat: add threshold preset list and editor Django views"
```

---

## Task 2: SCSS and nav link

**Files:**
- Create: `meals/static/meals/scss/threshold_preset.scss`
- Modify: `meals/templates/meals/base.html.j2` (add nav link)

### Step 1: Add the nav link to `base.html.j2`

In `meals/templates/meals/base.html.j2`, find the nav links block (around line 21–29). Add a new `<a>` after the Food Database link:

```django
<a href="{% url 'threshold-preset-list' %}"
   class="nav-link{% if request.resolver_match.url_name == 'threshold-preset-list' or request.resolver_match.url_name == 'threshold-preset-editor' %} active{% endif %}">
    {% trans "Thresholds" %}
</a>
```

### Step 2: Create `meals/static/meals/scss/threshold_preset.scss`

```scss
// ============================================================
// threshold_preset.scss – Threshold Preset list and editor pages
// ============================================================

@import 'variables';

body {
    align-items: center;
    padding-top: 0;
}

// ---- Shared: top actions bar ----
.top-actions {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
    align-items: center;

    @media (max-width: $bp-sm) {
        flex-direction: column;
        align-items: stretch;
    }
}

.btn-create {
    display: inline-flex;
    align-items: center;
    padding: 0.8rem 1.5rem;
    background: var(--primary);
    color: white;
    text-decoration: none;
    border-radius: 12px;
    font-weight: 400;
    transition: all 0.3s ease;
    box-shadow: 0 4px 10px var(--primary-glow);
    border: none;
    cursor: pointer;
    white-space: nowrap;
    font-size: 1rem;

    &:hover:not(:disabled) {
        background: var(--primary-hover);
        transform: translateY(-2px);
        box-shadow: 0 6px 15px var(--primary-glow);
    }

    &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }
}

.search-wrapper {
    position: relative;
    flex-grow: 1;
}

.search-bar {
    width: 100%;
    padding: 0.8rem 1.2rem;
    background: #ffffff;
    border: 1px solid var(--glass-border);
    border-radius: 12px;
    color: var(--text-main);
    font-size: 1rem;
    outline: none;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: var(--shadow);

    &:focus {
        border-color: var(--primary);
        box-shadow: 0 0 15px var(--primary-glow);
    }
}

.table-card {
    background: var(--card-bg);
    backdrop-filter: blur(12px);
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
    transition: opacity 0.3s ease;

    &.is-loading {
        opacity: 0.6;
        pointer-events: none;
    }
}

.empty-row {
    text-align: center;
    padding: 3rem;
    color: var(--text-dim);
}

.error-msg {
    color: var(--danger);
    text-align: center;
    margin-top: 1rem;
    font-size: 0.9rem;
}

// ---- Shared: expand/collapse animation (grid-template-rows trick) ----
.expanded-content {
    display: grid;
    grid-template-rows: 0fr;
    transition: grid-template-rows 0.3s ease;

    &.open {
        grid-template-rows: 1fr;
    }
}

.expanded-inner {
    overflow: hidden;
}

// ---- List: preset table ----
.preset-table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;

    th {
        padding: 1rem;
        font-weight: 600;
        color: var(--text-dim);
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 1px solid var(--glass-border);
    }

    td {
        padding: 0.9rem 1rem;
        border-bottom: 1px solid var(--glass-border);
        font-size: 0.9rem;
        transition: background 0.2s;
    }

    tr:last-child td {
        border-bottom: none;
    }
}

.preset-row {
    cursor: pointer;

    &:hover td {
        background: var(--row-hover);
    }
}

.preset-name-cell {
    font-weight: 400;
    color: var(--text-main);
    min-width: 160px;

    strong {
        color: var(--primary);
        font-weight: 600;
    }
}

.preset-nutrient-cell {
    color: var(--text-dim);
    font-size: 0.82rem;
    text-align: right;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}

.col-actions {
    text-align: right;
    white-space: nowrap;
    width: 70px;
}

.btn-icon-link,
.btn-expand-chevron {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-dim);
    padding: 4px 6px;
    border-radius: 6px;
    transition: color 0.2s, background 0.2s;
    line-height: 1;

    &:hover {
        color: var(--primary);
        background: var(--primary-glow);
    }
}

// Expanded nutrient grid inside a table row
.preset-expanded-inner {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 0.4rem 1rem;
    padding: 0;
    transition: padding 0.3s ease;
}

.open > .preset-expanded-inner {
    padding: 1rem 1.5rem;
}

.expanded-nutrient-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.83rem;
    gap: 0.5rem;
}

.expanded-nutrient-label {
    color: var(--text-dim);
}

.expanded-nutrient-val {
    color: var(--text-main);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}

// ---- Editor ----
.preset-editor-container {
    padding: 2rem 1rem;
}

.back-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--text-dim);
    text-decoration: none;
    font-size: 0.9rem;
    margin-bottom: 2rem;
    transition: color 0.2s;

    &:hover {
        color: var(--primary);
    }
}

.autosave-indicator {
    position: fixed;
    top: 70px;
    right: 20px;
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 500;
    z-index: 100;

    &.saving {
        background: rgba(0, 0, 0, 0.06);
        color: var(--text-dim);
    }

    &.saved {
        background: rgba(65, 166, 109, 0.15);
        color: var(--success);
    }

    &.error {
        background: rgba(166, 65, 67, 0.15);
        color: var(--danger);
    }
}

.preset-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 2rem;

    h1.preset-name-display {
        font-size: 2rem;
        font-weight: 400;
        background: linear-gradient(135deg, #4180A6 0%, $text-dim 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
}

.btn-edit-name {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-dim);
    padding: 6px;
    border-radius: 8px;
    transition: color 0.2s, background 0.2s;
    flex-shrink: 0;
    line-height: 1;

    &:hover {
        color: var(--primary);
        background: var(--primary-glow);
    }
}

.name-input {
    font-size: 2rem;
    font-weight: 400;
    border: none;
    border-bottom: 2px solid var(--primary);
    outline: none;
    background: transparent;
    color: var(--text-main);
    width: 100%;
    max-width: 500px;
}

.nutrient-card {
    background: var(--card-bg);
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
    margin-bottom: 2rem;
}

.nutrient-rows {
    padding: 0.25rem 0;
}

.nutrient-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1.5rem;
    border-bottom: 1px solid var(--glass-border);
    gap: 1rem;

    @media (max-width: $bp-sm) {
        flex-direction: column;
        align-items: flex-start;
    }
}

.nutrient-label {
    flex: 1;
    font-size: 0.95rem;
    color: var(--text-main);
}

.nutrient-unit {
    color: var(--text-dim);
    font-size: 0.85rem;
}

.nutrient-inputs {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
}

.input-label {
    font-size: 0.75rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.threshold-input {
    width: 90px;
    padding: 0.4rem 0.6rem;
    border: 1px solid var(--glass-border);
    border-radius: 8px;
    background: white;
    color: var(--text-main);
    font-size: 0.9rem;
    outline: none;
    transition: border-color 0.2s;
    font-variant-numeric: tabular-nums;

    &:focus {
        border-color: var(--primary);
    }

    &::-webkit-outer-spin-button,
    &::-webkit-inner-spin-button {
        -webkit-appearance: none;
    }

    -moz-appearance: textfield;
}

.expand-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0.9rem 1.5rem;
    width: 100%;
    border: none;
    border-top: 1px solid var(--glass-border);
    border-radius: 0;
    font-size: 0.9rem;
    color: var(--text-dim);
    background: transparent;
    cursor: pointer;
    text-align: left;
    transition: background 0.2s;

    &:hover {
        background: var(--row-hover);
    }
}

// Editor expanded section: list of nutrient rows inside the card
.editor-expanded-inner {
    overflow: hidden;
}

.danger-zone {
    padding-top: 1.5rem;
    border-top: 1px solid var(--glass-border);
    margin-top: 0.5rem;
}

.btn-danger {
    padding: 0.7rem 1.5rem;
    background: transparent;
    color: var(--danger);
    border: 1px solid var(--danger);
    border-radius: 10px;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
        background: var(--danger);
        color: white;
    }
}
```

### Step 3: Verify SCSS compiles

```bash
uv run python manage.py build_scss
```

Expected: no errors, `sass_cache/meals/scss/threshold_preset.css` created.

### Step 4: Commit

```bash
git add meals/static/meals/scss/threshold_preset.scss \
    meals/templates/meals/base.html.j2
git commit -m "feat: add threshold preset SCSS and nav link"
```

---

## Task 3: Vite entry point stubs

**Files:**
- Create: `frontend/src/threshold-preset-list/main.js` (stub)
- Create: `frontend/src/threshold-preset-editor/main.js` (stub)
- Modify: `vite.config.js`

### Step 1: Create stub entry points

Create `frontend/src/threshold-preset-list/main.js`:
```js
// Stub — replaced in Task 4
```

Create `frontend/src/threshold-preset-editor/main.js`:
```js
// Stub — replaced in Task 5
```

### Step 2: Add entries to `vite.config.js`

In `vite.config.js`, add two lines inside `rollupOptions.input`:

```js
'threshold-preset-list':   'frontend/src/threshold-preset-list/main.js',
'threshold-preset-editor': 'frontend/src/threshold-preset-editor/main.js',
```

The full `rollupOptions.input` block becomes:
```js
input: {
  'mealplan-list':           'frontend/src/mealplan-list/main.js',
  'mealplan-detail':         'frontend/src/mealplan-detail/main.js',
  'food-database':           'frontend/src/food-database/main.js',
  'food-editor':             'frontend/src/food-editor/main.js',
  'threshold-preset-list':   'frontend/src/threshold-preset-list/main.js',
  'threshold-preset-editor': 'frontend/src/threshold-preset-editor/main.js',
},
```

### Step 3: Verify build succeeds

```bash
pnpm build
```

Expected: build succeeds, two new asset files appear in `frontend/dist/assets/`.

### Step 4: Commit

```bash
git add vite.config.js \
    frontend/src/threshold-preset-list/main.js \
    frontend/src/threshold-preset-editor/main.js
git commit -m "chore: add threshold preset Vite entry point stubs"
```

---

## Task 4: List SPA — Playwright tests + Vue implementation

**Files:**
- Test: `tests/frontend/test_threshold_preset_list.py`
- Create: `frontend/src/threshold-preset-list/components/PresetSearchBar.vue`
- Create: `frontend/src/threshold-preset-list/components/PresetRow.vue`
- Create: `frontend/src/threshold-preset-list/components/PresetTable.vue`
- Create: `frontend/src/threshold-preset-list/components/ThresholdPresetApp.vue`
- Modify: `frontend/src/threshold-preset-list/main.js`

### Step 1: Write the failing Playwright tests

Create `tests/frontend/test_threshold_preset_list.py`:

```python
"""Playwright tests for the threshold preset list page."""

import pytest
from playwright.sync_api import expect
from tests.frontend.factories import ThresholdPresetFactory
from meals.models import ThresholdPreset

pytestmark = pytest.mark.django_db


def _goto_list(page, live_server):
    page.goto(live_server.url + "/threshold-presets/")
    page.wait_for_selector("#threshold-preset-list-app table", timeout=15000)


def test_list_shows_preset_name(logged_in_page, live_server):
    ThresholdPresetFactory(name="Adult Standard")
    _goto_list(logged_in_page, live_server)
    expect(logged_in_page.locator(".preset-name-cell").first).to_contain_text(
        "Adult Standard"
    )


def test_search_filters_presets(logged_in_page, live_server):
    ThresholdPresetFactory(name="Adult Standard")
    ThresholdPresetFactory(name="Child Standard")
    _goto_list(logged_in_page, live_server)
    logged_in_page.fill(".search-bar", "Adult")
    logged_in_page.wait_for_timeout(600)
    expect(logged_in_page.locator(".preset-name-cell")).to_have_count(1)
    expect(logged_in_page.locator(".preset-name-cell").first).to_contain_text(
        "Adult Standard"
    )


def test_search_highlights_match(logged_in_page, live_server):
    ThresholdPresetFactory(name="Adult Standard")
    _goto_list(logged_in_page, live_server)
    logged_in_page.fill(".search-bar", "Adult")
    logged_in_page.wait_for_timeout(600)
    strong = logged_in_page.locator(".preset-name-cell strong")
    expect(strong).to_have_count(1)
    expect(strong).to_contain_text("Adult")


def test_expand_chevron_reveals_more_nutrients(logged_in_page, live_server):
    ThresholdPresetFactory(name="Test Preset")
    _goto_list(logged_in_page, live_server)
    # Expanded content starts collapsed (grid-template-rows: 0fr means height 0)
    expanded = logged_in_page.locator(".expanded-content").first
    assert expanded.evaluate("el => el.clientHeight") == 0
    logged_in_page.locator(".btn-expand-chevron").first.click()
    logged_in_page.wait_for_timeout(400)
    assert expanded.evaluate("el => el.clientHeight") > 0


def test_create_button_navigates_to_editor(logged_in_page, live_server):
    _goto_list(logged_in_page, live_server)
    logged_in_page.click(".btn-create")
    logged_in_page.wait_for_url("**/threshold-presets/*/")
    assert "/threshold-presets/" in logged_in_page.url
    assert logged_in_page.url != live_server.url + "/threshold-presets/"


def test_clicking_name_navigates_to_editor(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="Click Me")
    _goto_list(logged_in_page, live_server)
    logged_in_page.locator(".preset-name-cell").first.click()
    logged_in_page.wait_for_url(f"**/threshold-presets/{preset.id}/")
    assert f"/threshold-presets/{preset.id}/" in logged_in_page.url


def test_empty_state_shown_when_no_presets(logged_in_page, live_server):
    ThresholdPreset.objects.all().delete()
    _goto_list(logged_in_page, live_server)
    expect(logged_in_page.locator(".empty-row")).to_be_visible()
```

### Step 2: Run tests to confirm they fail

```bash
uv run black . && uv run pytest tests/frontend/test_threshold_preset_list.py -v
```

Expected: tests FAIL — the Vue app is not mounted (stub main.js).

### Step 3: Create `frontend/src/threshold-preset-list/components/PresetSearchBar.vue`

This is identical in behaviour to `FoodSearchBar.vue`:

```vue
<template>
  <input
    type="text"
    class="search-bar"
    :placeholder="placeholder"
    :value="modelValue"
    autocomplete="off"
    @input="onInput"
    @keydown.enter.prevent
  />
</template>

<script setup>
const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

let timer = null

function onInput(e) {
  clearTimeout(timer)
  const value = e.target.value
  timer = setTimeout(() => {
    emit('update:modelValue', value)
  }, 300)
}
</script>
```

### Step 4: Create `frontend/src/threshold-preset-list/components/PresetRow.vue`

Note: This component renders **two** `<tr>` elements (Vue 3 supports multiple root nodes). The second row contains the collapsible nutrient grid.

```vue
<template>
  <tr class="preset-row" @click="navigate">
    <td class="preset-name-cell">
      <span v-html="highlightMatch(preset.name, searchQuery)"></span>
    </td>
    <td
      v-for="key in DEFAULT_KEYS"
      :key="key"
      class="preset-nutrient-cell"
    >
      {{ formatThreshold(preset[key + '_min'], preset[key + '_max']) }}
    </td>
    <td class="col-actions" @click.stop>
      <button class="btn-icon-link" @click="navigate" title="Edit">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
        </svg>
      </button>
      <button class="btn-expand-chevron" @click="expanded = !expanded">
        <svg
          width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
          :style="{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease' }"
        >
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>
    </td>
  </tr>
  <tr class="preset-expanded-row">
    <td :colspan="DEFAULT_KEYS.length + 2" style="padding: 0; border-bottom: 1px solid var(--glass-border);">
      <div class="expanded-content" :class="{ open: expanded }">
        <div class="preset-expanded-inner expanded-inner">
          <div
            v-for="nutrient in extendedNutrients"
            :key="nutrient.key"
            class="expanded-nutrient-item"
          >
            <span class="expanded-nutrient-label">{{ nutrient.label }} ({{ nutrient.unit }})</span>
            <span class="expanded-nutrient-val">
              {{ formatThreshold(preset[nutrient.key + '_min'], preset[nutrient.key + '_max']) }}
            </span>
          </div>
        </div>
      </div>
    </td>
  </tr>
</template>

<script setup>
import { ref, computed, inject } from 'vue'

const props = defineProps({
  preset: { type: Object, required: true },
  searchQuery: { type: String, default: '' },
})

const nutrients = inject('nutrients')
const presetEditorBaseUrl = inject('presetEditorBaseUrl')

const DEFAULT_KEYS = ['energy_in_kcal', 'water_in_g', 'carbohydrate_in_g', 'fat_in_g', 'protein_in_g']

const expanded = ref(false)

const extendedNutrients = computed(() =>
  nutrients.filter((n) => !DEFAULT_KEYS.includes(n.key))
)

function navigate() {
  window.location.href = presetEditorBaseUrl + props.preset.id + '/'
}

function formatThreshold(min, max) {
  if (min == null && max == null) return '—'
  const minStr = min != null ? String(min) : '—'
  const maxStr = max != null ? String(max) : '—'
  return `${minStr} / ${maxStr}`
}

function highlightMatch(text, query) {
  if (!query) return text
  const tokens = query
    .toLowerCase()
    .split(/\s+/)
    .filter((t) => t.length >= 2)
  if (tokens.length === 0) return text
  const pattern = tokens
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|')
  const regex = new RegExp(`(${pattern})`, 'gi')
  return text.replace(regex, '<strong>$1</strong>')
}
</script>
```

### Step 5: Create `frontend/src/threshold-preset-list/components/PresetTable.vue`

```vue
<template>
  <table class="preset-table">
    <thead>
      <tr>
        <th class="col-name">{{ i18n.colName }}</th>
        <th
          v-for="key in DEFAULT_KEYS"
          :key="key"
          class="col-nutrient preset-nutrient-cell"
        >
          {{ labelFor(key) }}
        </th>
        <th class="col-actions"></th>
      </tr>
    </thead>
    <tbody>
      <tr v-if="presets.length === 0 && !loading">
        <td :colspan="DEFAULT_KEYS.length + 2" class="empty-row">
          {{ i18n.noData }}
        </td>
      </tr>
      <PresetRow
        v-for="preset in presets"
        :key="preset.id"
        :preset="preset"
        :search-query="searchQuery"
      />
    </tbody>
  </table>
</template>

<script setup>
import { inject } from 'vue'
import PresetRow from './PresetRow.vue'

defineProps({
  presets: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  searchQuery: { type: String, default: '' },
})

const i18n = inject('i18n')
const nutrients = inject('nutrients')

const DEFAULT_KEYS = ['energy_in_kcal', 'water_in_g', 'carbohydrate_in_g', 'fat_in_g', 'protein_in_g']

function labelFor(key) {
  const n = nutrients.find((x) => x.key === key)
  return n ? `${n.label} (${n.unit})` : key
}
</script>
```

### Step 6: Create `frontend/src/threshold-preset-list/components/ThresholdPresetApp.vue`

```vue
<template>
  <div>
    <div class="top-actions">
      <button class="btn-create" @click="createPreset" :disabled="creating">
        <svg
          width="20" height="20" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round"
          stroke-linejoin="round" style="margin-right: 8px;"
        >
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        {{ i18n.createPreset }}
      </button>
      <div class="search-wrapper">
        <PresetSearchBar v-model="searchQuery" :placeholder="i18n.searchPlaceholder" />
      </div>
    </div>

    <div class="table-card" :class="{ 'is-loading': loading }">
      <PresetTable
        :presets="presets"
        :loading="loading"
        :search-query="searchQuery"
      />
    </div>

    <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, inject } from 'vue'
import PresetSearchBar from './PresetSearchBar.vue'
import PresetTable from './PresetTable.vue'

const csrfToken = inject('csrfToken')
const i18n = inject('i18n')
const presetEditorBaseUrl = inject('presetEditorBaseUrl')

const presets = ref([])
const loading = ref(true)
const searchQuery = ref('')
const creating = ref(false)
const errorMsg = ref('')

async function fetchAll() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await fetch('/api/threshold-presets/')
    if (!res.ok) throw new Error(res.status)
    const data = await res.json()
    presets.value = data.results ?? (Array.isArray(data) ? data : [])
  } catch (e) {
    errorMsg.value = i18n.networkError ?? 'Network error'
  } finally {
    loading.value = false
  }
}

async function doSearch(query) {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await fetch(
      `/api/threshold-presets/?search=${encodeURIComponent(query)}`
    )
    if (!res.ok) throw new Error(res.status)
    const data = await res.json()
    presets.value = data.results ?? (Array.isArray(data) ? data : [])
  } catch (e) {
    errorMsg.value = i18n.networkError ?? 'Network error'
  } finally {
    loading.value = false
  }
}

async function createPreset() {
  creating.value = true
  errorMsg.value = ''
  try {
    const res = await fetch('/api/threshold-presets/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ name: i18n.newPresetName }),
    })
    if (!res.ok) throw new Error(res.status)
    const preset = await res.json()
    window.location.href = presetEditorBaseUrl + preset.id + '/'
  } catch (e) {
    errorMsg.value = i18n.errorCreate ?? 'Error creating preset'
  } finally {
    creating.value = false
  }
}

let searchTimer = null
watch(searchQuery, (q) => {
  clearTimeout(searchTimer)
  if (q.length >= 2) {
    searchTimer = setTimeout(() => doSearch(q), 0)
  } else if (q.length === 0) {
    fetchAll()
  }
})

onMounted(() => {
  fetchAll()
})
</script>
```

### Step 7: Replace `frontend/src/threshold-preset-list/main.js` with the real entry point

```js
import { createApp } from 'vue'
import ThresholdPresetApp from './components/ThresholdPresetApp.vue'

const el = document.getElementById('threshold-preset-list-app')
const app = createApp(ThresholdPresetApp)

app.provide('csrfToken', el.dataset.csrfToken)
app.provide('presetEditorBaseUrl', el.dataset.presetEditorBaseUrl)
app.provide('nutrients', JSON.parse(el.dataset.nutrients))
app.provide('i18n', JSON.parse(el.dataset.i18n))

app.mount(el)
```

### Step 8: Build and run tests

```bash
pnpm build
```

Expected: build succeeds.

```bash
uv run black . && uv run pytest tests/frontend/test_threshold_preset_list.py -v --create-db
```

Expected: all 7 tests PASS.

### Step 9: Commit

```bash
git add \
    frontend/src/threshold-preset-list/main.js \
    frontend/src/threshold-preset-list/components/ \
    tests/frontend/test_threshold_preset_list.py
git commit -m "feat: add threshold preset list SPA"
```

---

## Task 5: Editor SPA — Playwright tests + Vue implementation

**Files:**
- Test: `tests/frontend/test_threshold_preset_editor.py`
- Create: `frontend/src/threshold-preset-editor/components/ThresholdPresetEditorApp.vue`
- Modify: `frontend/src/threshold-preset-editor/main.js`

### Step 1: Write the failing Playwright tests

Create `tests/frontend/test_threshold_preset_editor.py`:

```python
"""Playwright tests for the threshold preset editor page."""

import pytest
from playwright.sync_api import expect
from tests.frontend.factories import ThresholdPresetFactory
from meals.models import ThresholdPreset

pytestmark = pytest.mark.django_db


def _goto_editor(page, live_server, preset):
    page.goto(live_server.url + f"/threshold-presets/{preset.id}/")
    page.wait_for_selector("#threshold-preset-editor-app .preset-header", timeout=15000)


def test_editor_shows_preset_name(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="Adults")
    _goto_editor(logged_in_page, live_server, preset)
    expect(logged_in_page.locator(".preset-name-display")).to_contain_text("Adults")


def test_edit_name_via_pencil_icon(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="Old Name")
    _goto_editor(logged_in_page, live_server, preset)
    logged_in_page.click(".btn-edit-name")
    logged_in_page.fill(".name-input", "New Name")
    logged_in_page.locator(".name-input").blur()
    logged_in_page.wait_for_timeout(600)
    updated = ThresholdPreset.objects.get(pk=preset.id)
    assert updated.name == "New Name"


def test_autosave_indicator_shows_saved_after_blur(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="Test")
    _goto_editor(logged_in_page, live_server, preset)
    logged_in_page.locator(".nutrient-min-input").first.fill("1800")
    logged_in_page.locator(".nutrient-min-input").first.blur()
    expect(logged_in_page.locator(".autosave-indicator")).to_contain_text("Saved")


def test_nutrient_value_persisted_after_blur(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="Test", energy_in_kcal_min=None)
    _goto_editor(logged_in_page, live_server, preset)
    logged_in_page.locator(".nutrient-min-input").first.fill("2000")
    logged_in_page.locator(".nutrient-min-input").first.blur()
    logged_in_page.wait_for_timeout(600)
    updated = ThresholdPreset.objects.get(pk=preset.id)
    assert updated.energy_in_kcal_min == 2000.0


def test_expand_chevron_reveals_extended_nutrients(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="Test")
    _goto_editor(logged_in_page, live_server, preset)
    expanded = logged_in_page.locator(".expanded-content")
    assert expanded.evaluate("el => el.clientHeight") == 0
    logged_in_page.click(".btn-expand-chevron")
    logged_in_page.wait_for_timeout(400)
    assert expanded.evaluate("el => el.clientHeight") > 0


def test_delete_preset_redirects_to_list(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="ToDelete")
    _goto_editor(logged_in_page, live_server, preset)
    logged_in_page.on("dialog", lambda d: d.accept())
    logged_in_page.click(".btn-danger")
    logged_in_page.wait_for_url("**/threshold-presets/")
    assert not ThresholdPreset.objects.filter(pk=preset.id).exists()


def test_back_link_returns_to_list(logged_in_page, live_server):
    preset = ThresholdPresetFactory(name="Test")
    _goto_editor(logged_in_page, live_server, preset)
    logged_in_page.click(".back-link")
    expect(logged_in_page).to_have_url(live_server.url + "/threshold-presets/")
```

### Step 2: Run tests to confirm they fail

```bash
uv run pytest tests/frontend/test_threshold_preset_editor.py -v --create-db
```

Expected: all tests FAIL — stub entry point is not mounting a Vue app.

### Step 3: Create `frontend/src/threshold-preset-editor/components/ThresholdPresetEditorApp.vue`

```vue
<template>
  <div class="preset-editor-container">
    <!-- Back link -->
    <a :href="presetListUrl" class="back-link">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="15 18 9 12 15 6"></polyline>
      </svg>
      {{ i18n.backToList }}
    </a>

    <!-- Autosave indicator -->
    <div
      class="autosave-indicator"
      :class="saveStatus"
      v-show="saveStatus !== 'idle'"
    >
      <span v-if="saveStatus === 'saving'">{{ i18n.saving }}</span>
      <span v-else-if="saveStatus === 'saved'">{{ i18n.saved }}</span>
      <span v-else-if="saveStatus === 'error'">{{ i18n.errorSaving }}</span>
    </div>

    <div v-if="notFound" class="error-msg">{{ i18n.notFound }}</div>

    <template v-else-if="preset">
      <!-- Name header -->
      <div class="preset-header">
        <template v-if="!editingName">
          <h1 class="preset-name-display">{{ preset.name }}</h1>
          <button class="btn-edit-name" @click="startEditName">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2" stroke-linecap="round"
                 stroke-linejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
          </button>
        </template>
        <template v-else>
          <input
            ref="nameInputEl"
            class="name-input"
            v-model="editName"
            @blur="saveName"
            @keydown.enter="nameInputEl.blur()"
            @keydown.escape="cancelEditName"
          />
        </template>
      </div>

      <!-- Nutrient card -->
      <div class="nutrient-card">
        <div class="nutrient-rows">
          <div
            v-for="nutrient in defaultNutrients"
            :key="nutrient.key"
            class="nutrient-row"
          >
            <span class="nutrient-label">
              {{ nutrient.label }}
              <span class="nutrient-unit">({{ nutrient.unit }})</span>
            </span>
            <div class="nutrient-inputs">
              <span class="input-label">{{ i18n.min }}</span>
              <input
                class="nutrient-min-input threshold-input"
                type="number"
                step="any"
                :value="preset[nutrient.key + '_min'] ?? ''"
                @blur="saveField(nutrient.key + '_min', $event.target.value)"
                :placeholder="i18n.min"
              />
              <span class="input-label">{{ i18n.max }}</span>
              <input
                class="nutrient-max-input threshold-input"
                type="number"
                step="any"
                :value="preset[nutrient.key + '_max'] ?? ''"
                @blur="saveField(nutrient.key + '_max', $event.target.value)"
                :placeholder="i18n.max"
              />
            </div>
          </div>
        </div>

        <!-- Expand toggle -->
        <button class="btn-expand-chevron expand-toggle" @click="expanded = !expanded">
          <svg
            width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2" stroke-linecap="round"
            stroke-linejoin="round"
            :style="{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease' }"
          >
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
          {{ expanded ? i18n.showLess : i18n.showMore }}
        </button>

        <!-- Expanded nutrients -->
        <div class="expanded-content" :class="{ open: expanded }">
          <div class="editor-expanded-inner expanded-inner">
            <div
              v-for="nutrient in extendedNutrients"
              :key="nutrient.key"
              class="nutrient-row"
              style="border-top: 1px solid var(--glass-border);"
            >
              <span class="nutrient-label">
                {{ nutrient.label }}
                <span class="nutrient-unit">({{ nutrient.unit }})</span>
              </span>
              <div class="nutrient-inputs">
                <span class="input-label">{{ i18n.min }}</span>
                <input
                  class="nutrient-min-input threshold-input"
                  type="number"
                  step="any"
                  :value="preset[nutrient.key + '_min'] ?? ''"
                  @blur="saveField(nutrient.key + '_min', $event.target.value)"
                  :placeholder="i18n.min"
                />
                <span class="input-label">{{ i18n.max }}</span>
                <input
                  class="nutrient-max-input threshold-input"
                  type="number"
                  step="any"
                  :value="preset[nutrient.key + '_max'] ?? ''"
                  @blur="saveField(nutrient.key + '_max', $event.target.value)"
                  :placeholder="i18n.max"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Delete -->
      <div class="danger-zone">
        <button class="btn-danger" @click="deletePreset">
          {{ i18n.deletePreset }}
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, nextTick } from 'vue'

const presetId = inject('presetId')
const csrfToken = inject('csrfToken')
const nutrients = inject('nutrients')
const i18n = inject('i18n')
const presetListUrl = inject('presetListUrl')

const DEFAULT_KEYS = [
  'energy_in_kcal',
  'water_in_g',
  'carbohydrate_in_g',
  'fat_in_g',
  'protein_in_g',
]

const preset = ref(null)
const notFound = ref(false)
const saveStatus = ref('idle')
const editingName = ref(false)
const editName = ref('')
const nameInputEl = ref(null)
const expanded = ref(false)

const defaultNutrients = computed(() =>
  nutrients.filter((n) => DEFAULT_KEYS.includes(n.key))
)
const extendedNutrients = computed(() =>
  nutrients.filter((n) => !DEFAULT_KEYS.includes(n.key))
)

async function loadPreset() {
  try {
    const res = await fetch(`/api/threshold-presets/${presetId}/`)
    if (res.status === 404) {
      notFound.value = true
      return
    }
    if (!res.ok) throw new Error(res.status)
    preset.value = await res.json()
  } catch (e) {
    notFound.value = true
  }
}

async function patch(data) {
  saveStatus.value = 'saving'
  try {
    const res = await fetch(`/api/threshold-presets/${presetId}/`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error(res.status)
    preset.value = await res.json()
    saveStatus.value = 'saved'
    setTimeout(() => {
      if (saveStatus.value === 'saved') saveStatus.value = 'idle'
    }, 2000)
  } catch (e) {
    saveStatus.value = 'error'
  }
}

async function saveField(fieldName, rawValue) {
  const value = rawValue === '' ? null : parseFloat(rawValue)
  await patch({ [fieldName]: value })
}

function startEditName() {
  editName.value = preset.value.name
  editingName.value = true
  nextTick(() => nameInputEl.value?.focus())
}

function cancelEditName() {
  editingName.value = false
}

async function saveName() {
  const name = editName.value.trim()
  editingName.value = false
  if (!name || name === preset.value.name) return
  await patch({ name })
}

async function deletePreset() {
  if (!window.confirm(i18n.deleteConfirm)) return
  saveStatus.value = 'saving'
  try {
    const res = await fetch(`/api/threshold-presets/${presetId}/`, {
      method: 'DELETE',
      headers: { 'X-CSRFToken': csrfToken },
    })
    if (!res.ok) throw new Error(res.status)
    window.location.href = presetListUrl
  } catch (e) {
    saveStatus.value = 'error'
  }
}

onMounted(loadPreset)
</script>
```

### Step 4: Replace `frontend/src/threshold-preset-editor/main.js`

```js
import { createApp } from 'vue'
import ThresholdPresetEditorApp from './components/ThresholdPresetEditorApp.vue'

const el = document.getElementById('threshold-preset-editor-app')
const app = createApp(ThresholdPresetEditorApp)

app.provide('presetId', el.dataset.presetId)
app.provide('csrfToken', el.dataset.csrfToken)
app.provide('nutrients', JSON.parse(el.dataset.nutrients))
app.provide('i18n', JSON.parse(el.dataset.i18n))
app.provide('presetListUrl', el.dataset.presetListUrl)

app.mount(el)
```

### Step 5: Build and run all tests

```bash
pnpm build
```

Expected: build succeeds.

```bash
uv run black . && uv run pytest tests/frontend/test_threshold_preset_editor.py -v --create-db
```

Expected: all 7 tests PASS.

Run the full suite to check for regressions:

```bash
uv run pytest tests/test_threshold_preset_views.py tests/frontend/test_threshold_preset_list.py tests/frontend/test_threshold_preset_editor.py -v
```

Expected: all tests PASS.

### Step 6: Commit

```bash
git add \
    frontend/src/threshold-preset-editor/main.js \
    frontend/src/threshold-preset-editor/components/ \
    tests/frontend/test_threshold_preset_editor.py
git commit -m "feat: add threshold preset editor SPA"
```

---

## Final check

Run the full test suite before declaring done:

```bash
uv run black . && uv run pytest tests/test_*.py tests/api/ tests/frontend/ -v
```

Expected: all existing tests still PASS alongside the new ones.
