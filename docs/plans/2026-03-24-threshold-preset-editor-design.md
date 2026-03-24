# Threshold Preset Editor — Design

**Goal:** Add a dedicated Threshold Preset section (list + editor) accessible from the top navigation bar.

**Architecture:** Two separate Vue 3 SPAs — one for the list/overview page, one for the editor page — mirroring the existing food-database + food-editor pattern. The existing `/api/threshold-presets/` DRF endpoint is used as-is. A new Django URL, view, and template are added for each page, plus one shared SCSS file.

---

## Overview Page (`/threshold-presets/`)

### Navigation
- Add a "Threshold Presets" link to `base.html.j2` nav bar, between "Food Database" and the user info area.
- Active state follows the same `request.resolver_match.url_name` pattern as existing links.

### Django layer
- New view `threshold_preset_list` (login_required) in `meals/views.py` — renders `meals/threshold_preset_list.html.j2`.
- New URL `/threshold-presets/` named `threshold-preset-list`.
- Template passes `csrf_token` and `data-i18n` JSON to the Vue mount element.

### Vue SPA (`frontend/src/threshold-preset-list/`)
New Vite entry point. Components:

| Component | Responsibility |
|---|---|
| `ThresholdPresetApp.vue` | Root: fetches presets, owns search query + loading state |
| `PresetSearchBar.vue` | 300ms debounced input, emits `update:modelValue` |
| `PresetTable.vue` | Table shell with thead |
| `PresetRow.vue` | One preset row: name + default nutrients + chevron + expanded nutrients |

**Search:** Server-side via `GET /api/threshold-presets/?search=<query>`. Fetches all presets on load (no pagination — dataset will be small). On query ≥ 2 chars, hits API after 300ms debounce. Highlights matched substrings in the name column using the same `highlightMatch` pattern as `FoodRow.vue`.

**Columns (always visible):** Name, kcal (min/max), water (min/max), carbs (min/max), fat (min/max), protein (min/max), chevron toggle.

**Expand/collapse:** Clicking the chevron in a row toggles a second `<tr>` containing the remaining 21 nutrients in a grid. Uses CSS `max-height` transition for smooth animation. Chevron SVG rotates 180° when expanded.

**Navigation to editor:** Clicking anywhere on the name cell, or the pencil icon in the last column, navigates to `/threshold-presets/<id>/`.

**Create button:** POSTs `{ name: "New Preset" }` to `/api/threshold-presets/`, then navigates to the new preset's editor page.

---

## Editor Page (`/threshold-presets/<id>/`)

### Django layer
- New view `threshold_preset_editor` (login_required) in `meals/views.py` — renders `meals/threshold_preset_editor.html.j2`.
- New URL `/threshold-presets/<int:pk>/` named `threshold-preset-editor`.
- Template passes `preset_id`, `csrf_token`, `nutrients_json`, and `i18n_json` (same nutrients list shape as food editor).

### Vue SPA (`frontend/src/threshold-preset-editor/`)
New Vite entry point. Single component: `ThresholdPresetEditorApp.vue`.

**Name editing:** Name displayed as static text with a pencil icon to the right. Clicking either activates an inline `<input>`. On blur, PATCHes `/api/threshold-presets/<id>/` with `{ name }`.

**Nutrient rows:** Same default/expanded structure as the list page. Each row has:
- Nutrient label + unit
- Min number input (nullable — empty string treated as `null`)
- Max number input (nullable)
- On `blur` of either input, fires a PATCH with the updated `_min`/`_max` field.

**Auto-save indicator:** Fixed top-right corner. States: idle (hidden), "Saving…" (spinner), "Saved ✓" (fades out after 2s), "Error saving" (stays until next save attempt).

**Expand/collapse:** Same chevron toggle as the list page — collapses the 21 non-default nutrients.

**Delete:** Red "Delete preset" button at the bottom. Calls `window.confirm`, then DELETEs `/api/threshold-presets/<id>/`, then redirects to `/threshold-presets/`.

**Back link:** "← Back to Threshold Presets" link at the top.

---

## SCSS

One new file `meals/static/meals/scss/threshold_preset.scss` — shared by both templates. Reuses existing variables, `.top-actions`, `.btn-create`, `.search-bar`, `.table-card`, `.food-table` patterns. Adds:
- `.preset-row` (clickable, hover highlight)
- `.nutrient-expanded-row` (collapsible second row, `max-height` transition)
- `.chevron-icon` (rotates on expand)
- `.autosave-indicator` (fixed position, fade transition)
- `.name-editor` (inline input styling)

---

## Vite Entry Points

Add two entries to `vite.config.js`:
```js
'threshold-preset-list':   'frontend/src/threshold-preset-list/main.js',
'threshold-preset-editor': 'frontend/src/threshold-preset-editor/main.js',
```

---

## Default Nutrients (always visible in table/editor)

`energy_in_kcal`, `water_in_g`, `carbohydrate_in_g`, `fat_in_g`, `protein_in_g`

All remaining nutrients in `NUTRIENTS` order are in the expandable section.

---

## Out of Scope

- Pagination on the preset list (dataset is small)
- Bulk delete
- Preset duplication/copy
