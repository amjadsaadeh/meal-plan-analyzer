# CLAUDE.md — AI Assistant Guide for RSOS Meal Planner

## Project Overview

RSOS Meal Planner is a Django 6.0 web application for meal planning and nutritional analysis. Food data is sourced from the **Bundes Lebensmittel Schlüssel (BLS)** — the German national food composition database. Users can create meal plans, assign foods to daily meals, track nutrient totals against configurable thresholds, and export plans as PDFs.

---

## Package Manager

**Always use `uv` — never use `pip` or bare `python` directly.**

```bash
uv sync                    # install/sync all dependencies
uv add <package>           # add a new dependency
uv run python manage.py …  # run any Django management command
uv run pytest              # run the test suite
```

`uv.lock` must stay in sync with `pyproject.toml`; commit both when dependencies change.

---

## Running the Application

### Local development (SQLite)

```bash
uv sync
cp .env.example .env       # fill in SECRET_KEY at minimum
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

### Docker Compose (PostgreSQL)

```bash
docker compose up
```

The compose stack runs four services: **db** (PostgreSQL 16), **redis** (Redis 7), **web** (Django + gunicorn on port 8000), and **worker** (Celery). The web service automatically runs `migrate`, `build_scss`, and `collectstatic` on startup. The worker and web services share a media volume.

---

## Code Formatting

**Always run `black` before running tests.** The CI pipeline enforces Black formatting and will fail if files are not formatted.

```bash
uv run black .             # format all Python files
uv run black --check .     # check formatting without modifying files
```

---

## Running Tests

**Always run `black .` before running tests** to avoid CI failures due to formatting.

```bash
uv run black . && uv run pytest              # format then run full suite
uv run pytest              # full suite (API + frontend)
uv run pytest tests/api/   # API tests only
uv run pytest tests/frontend/  # Playwright browser tests only
uv run pytest tests/test_*.py  # top-level unit/integration tests only
```

`pytest.ini` sets:
- `DJANGO_SETTINGS_MODULE = config.settings`
- `--reuse-db` (the test database is reused across runs; use `--create-db` to force rebuild)

The session-scoped `django_db_setup` fixture in `tests/conftest.py` auto-loads `tests/data/food_fixtures.json`.

Frontend tests use **Playwright** (`pytest-playwright`). They require a running live server (pytest-django's `live_server` fixture handles this automatically). Playwright must be installed with:
```bash
uv run playwright install --with-deps chromium
```

Before running frontend tests locally, compile SCSS:
```bash
uv run python manage.py build_scss
```

---

## Project Structure

```
meal-plan-analyzer/
├── config/                  # Django project configuration
│   ├── settings.py          # Settings via django-environ (.env)
│   ├── urls.py              # Root URL conf (delegates to meals.urls)
│   ├── wsgi.py / asgi.py
│   └── __init__.py
│
├── meals/                   # The sole Django app
│   ├── models.py            # Data models (see below)
│   ├── views.py             # Template views + DRF ViewSets
│   ├── serializers.py       # DRF serializers
│   ├── urls.py              # URL patterns for views and API router
│   ├── nutrients.py         # NUTRIENTS dict, NUTRIENT_IDS, THRESHOLD_SCHEMA
│   ├── admin.py             # Django admin registration
│   ├── apps.py
│   ├── locale/              # i18n translation files (de, en)
│   │   ├── de/LC_MESSAGES/django.po
│   │   └── en/LC_MESSAGES/django.po
│   ├── templatetags/
│   │   └── meal_extras.py   # Custom template filters
│   ├── templates/meals/     # Django template engine (.html.j2 files)
│   ├── static/meals/
│   │   ├── img/             # Static assets (logo, etc.)
│   │   └── scss/            # SCSS source files
│   ├── migrations/          # Django migrations (0001–0026)
│   ├── tasks.py             # Celery async tasks (PDF generation)
│   └── management/commands/  # Django management commands
│       ├── import_foods.py  # BLS Excel import command
│       └── build_scss.py    # SCSS compilation command
│
├── tests/
│   ├── conftest.py          # Shared fixtures (api_client, user, authenticated_client)
│   ├── data/
│   │   ├── food_fixtures.json     # Seed data for tests
│   │   ├── test_foods.xlsx        # Excel file for import tests
│   │   ├── test_foods_Daten.zip   # ZIP file containing BLS Daten file for import tests
│   │   └── test_foods_no_daten.zip  # ZIP file without Daten file for import error tests
│   ├── api/
│   │   ├── test_foods.py
│   │   ├── test_mealplans.py
│   │   ├── test_mealplandays.py
│   │   ├── test_mealplan_foods.py
│   │   ├── test_threshold_presets.py
│   │   ├── test_food_search_semantics.py
│   │   ├── test_export_name_auto_alias.py
│   │   ├── test_export_jobs.py
│   │   ├── test_food_energy_sync.py
│   │   └── test_food_aliases.py
│   ├── frontend/
│   │   ├── conftest.py      # Playwright fixtures (logged_in_page)
│   │   ├── factories.py     # factory-boy factories
│   │   ├── test_mealplan_list.py
│   │   ├── test_mealplan_detail.py
│   │   ├── test_food_editor.py
│   │   └── test_pdf.py
│   ├── test_admin.py
│   ├── test_error_handling.py
│   ├── test_extended_backend.py
│   ├── test_food_import.py
│   ├── test_meal_plan_context.py
│   ├── test_model_constraints.py
│   ├── test_model_validation.py
│   ├── test_nutrients.py
│   ├── test_pdf_views.py
│   ├── test_search_utilities.py
│   ├── test_template_filters.py
│   └── generate_test_data.py
│
├── frontend/                # Vue 3 / Vite SPA sources
│   └── src/                 # Component trees (mealplan-list, mealplan-detail, food-database, food-editor)
├── deployment/              # Kubernetes manifests and Ansible playbooks
├── docs/                    # Development plans and documentation
├── AGENTS.md                # Coding agent guidelines
├── pyproject.toml           # Project metadata and dependencies
├── pytest.ini
├── Dockerfile               # Multi-stage build (builder → python:3.12-slim)
├── docker-compose.yml
├── .env.example             # Environment variable template
├── .python-version          # Python 3.12
├── agent.md                 # Top-level agent guidelines (uv usage)
└── .agent/                  # AI agent rules and workflows
    ├── rules/
    │   ├── backend-package-manager.md
    │   ├── running-backend-tests.md
    │   └── command-whitelist.md
    └── workflows/
        └── run-tests.md
```

---

## Data Models (`meals/models.py`)

### `Food`
Represents a food item from the BLS database.

| Field | Type | Notes |
|---|---|---|
| `bls_code` | CharField(50) | Unique BLS identifier |
| `name` | CharField(255) | Food name |
| `energy_in_kj_per_100g` | FloatField | |
| `energy_in_kcal_per_100g` | FloatField | |
| `protein_in_g_per_100g` | FloatField | default 0.0 |
| `fat_in_g_per_100g` | FloatField | default 0.0 |
| `carbohydrate_in_g_per_100g` | FloatField | default 0.0 |
| `fibre_in_g_per_100g` | FloatField | default 0.0 |
| `water_in_g_per_100g` | FloatField | default 0.0 |
| `iron_in_mg_per_100g` | FloatField | default 0.0 |
| `sugar_in_g_per_100g` | FloatField | default 0.0 |
| `omega3_in_g_per_100g` | FloatField | default 0.0 |
| `vitc_in_mg_per_100g` | FloatField | Vitamin C; default 0.0 |
| `magnesium_in_mg_per_100g` | FloatField | default 0.0 |
| `zinc_in_mg_per_100g` | FloatField | default 0.0 |
| `vitb12_in_mug_per_100g` | FloatField | Vitamin B12 (µg); default 0.0 |
| `vita_in_mug_per_100g` | FloatField | Vitamin A (µg); default 0.0 |
| `calcium_in_mg_per_100g` | FloatField | default 0.0 |
| `vitd_in_mug_per_100g` | FloatField | Vitamin D (µg); default 0.0 |
| `vitb1_in_mg_per_100g` | FloatField | Vitamin B1 (thiamine); default 0.0 |
| `vitb2_in_mg_per_100g` | FloatField | Vitamin B2 (riboflavin); default 0.0 |
| `vitb3_in_mg_per_100g` | FloatField | Vitamin B3 (niacin); default 0.0 |
| `vitb5_in_mg_per_100g` | FloatField | Vitamin B5; default 0.0 |
| `vitb6_in_mug_per_100g` | FloatField | Vitamin B6 (µg); default 0.0 |
| `biotin_in_mug_per_100g` | FloatField | Biotin (µg); default 0.0 |
| `iodine_in_mug_per_100g` | FloatField | Iodine (µg); default 0.0 |
| `copper_in_mug_per_100g` | FloatField | Copper (µg); default 0.0 |
| `manganese_in_mug_per_100g` | FloatField | Manganese (µg); default 0.0 |
| `molybdenum_in_mug_per_100g` | FloatField | Molybdenum (µg); default 0.0 |
| `data_source` | CharField(blank) | Origin of the record; `''` for BLS-imported foods, `'custom'` for user-created foods |

### `FoodAlias`
Alternative name/synonym for a `Food` item, used during search.

- `food` — FK → `Food` (related_name `aliases`; CASCADE delete)
- `alias` — CharField(255)
- Unique constraint: `(food, alias)`
- The alias index is cached in Django's cache backend (key `food_aliases_index`; 1-hour TTL). Cache is invalidated automatically via `post_save`/`post_delete` signals on `FoodAlias`.
- `get_alias_index()` — module-level helper that returns a `dict[food_id → list[alias_string]]`.

### `MealPlan`
A named collection of days.

- `name` — default `"Neuer Plan"`
- `subtitle` — CharField(500, blank); optional subtitle shown on PDFs
- `creation_date` / `change_date` — auto timestamps; ordered by `-creation_date`
- `visible_nutrients` — JSON list of nutrient keys (defaults to all); validated against `NUTRIENT_IDS`
- `thresholds` — JSON dict `{ nutrient_key: { "min": float|null, "max": float|null } }`; validated by `THRESHOLD_SCHEMA`
- `clean()` migrates legacy nutrient key names automatically (e.g. `protein` → `protein_in_g`, `kcal` → `energy_in_kcal`)
- `save()` calls `full_clean()` — model-level validation always runs on save

### `MealPlanDay`
One day within a meal plan.

- `name` — default `"Neuer Tag"`
- `meal_plan` — FK → `MealPlan` (nullable, CASCADE); related_name `days`
- `creation_date` / `change_date` — auto timestamps; ordered by `-creation_date`
- `foods` — M2M → `Food` via `MealPlanFood`
- `removed` — soft-delete flag (default `False`); active days are always filtered with `removed=False`

### `MealPlanFood`
Junction table between `MealPlanDay` and `Food`.

- `meal_plan_day` — FK → `MealPlanDay` (CASCADE)
- `food` — FK → `Food` (CASCADE)
- `amount_in_g` — FloatField
- `meal_type` — choices: `breakfast`, `lunch`, `dinner` (TextChoices `MealType`)
- `export_name` — CharField(255, blank, default `''`); custom display name for PDF exports. When set and the name is not already findable via food search, it is automatically added as a `FoodAlias` for the food.
- Unique constraint: `(meal_plan_day, food, meal_type)`

### `ThresholdPreset`
Reusable named threshold presets. Has `_min` / `_max` FloatField pairs (nullable) for every nutrient tracked in `NUTRIENTS`, plus `energy_in_kj_min`/`_max`.

### `SiteSettings`
Singleton model for site-wide settings.

- `logo` — FileField (uploaded to `logos/`); used as the logo in PDF exports. Falls back to the static `meals/img/logo.png` if not set.
- `minilogo` — FileField (uploaded to `logos/`); 50×50 px logo on top-right of every PDF page except first. Falls back to nothing if not set.
- `pdf_footer_line_content` — TextField(max_length=500, blank=True, default `''`); light-gray left-aligned footer text shown on every PDF page.
- Enforces singleton via `save()` (always sets `pk=1`) and `SiteSettings.get()` classmethod.
- Admin: list view auto-redirects to the single instance; add/delete are disabled.

### `BackgroundJob`
Tracks async task execution (e.g. PDF generation via Celery).

- `id` — UUIDField (primary key, auto-generated)
- `task_type` — CharField(50); currently only `"pdf_export"`
- `status` — TextChoices: `PENDING`, `RUNNING`, `DONE`, `FAILED` (default `PENDING`)
- `progress` — PositiveSmallIntegerField (0–100 percentage)
- `task_kwargs` — JSONField; stores task parameters (e.g. `meal_plan_pk`, `language`)
- `result_file` — FileField (uploaded to `exports/`); the generated PDF, set when `status=DONE`
- `error_message` — TextField; populated on failure; truncated to 1000 chars
- `expires_at` — DateTimeField (nullable); set to 24 hours after creation
- `created_at`, `updated_at` — auto timestamps; ordered by `-created_at`

---

## Nutrients (`meals/nutrients.py`)

All nutrient logic flows through the `NUTRIENTS` ordered dict. Each entry maps a **nutrient key** to its label (translated via `gettext_lazy`), unit, the corresponding `Food` model field (`food_key`), and a `precision` for decimal display.

| Nutrient key | Label (i18n) | Unit | Precision |
|---|---|---|---|
| `energy_in_kcal` | Energy | kcal | 1 |
| `water_in_g` | Water | g | 1 |
| `protein_in_g` | Protein | g | 1 |
| `fat_in_g` | Fat | g | 1 |
| `omega3_in_g` | n-3 | g | 2 |
| `carbohydrate_in_g` | Carbs | g | 1 |
| `sugar_in_g` | Sugar | g | 1 |
| `fibre_in_g` | Fiber | g | 1 |
| `iron_in_mg` | Iron | mg | 1 |
| `vitc_in_mg` | Vit. C | mg | 1 |
| `magnesium_in_mg` | Mg | mg | 1 |
| `zinc_in_mg` | Zinc | mg | 1 |
| `vitb12_in_mug` | Vit. B12 | µg | 2 |
| `vita_in_mug` | Vit. A | µg | 1 |
| `calcium_in_mg` | Ca | mg | 1 |
| `vitd_in_mug` | Vit. D | µg | 2 |
| `vitb1_in_mg` | Vit. B1 | mg | 2 |
| `vitb2_in_mg` | Vit. B2 | mg | 2 |
| `vitb3_in_mg` | Vit. B3 | mg | 2 |
| `vitb5_in_mg` | Vit. B5 | mg | 2 |
| `vitb6_in_mug` | Vit. B6 | µg | 1 |
| `biotin_in_mug` | Biotin | µg | 1 |
| `iodine_in_mug` | Iodine | µg | 1 |
| `copper_in_mug` | Copper | µg | 1 |
| `manganese_in_mug` | Manganese | µg | 1 |
| `molybdenum_in_mug` | Molybdenum | µg | 1 |

`NUTRIENT_IDS` is the list of all keys. `THRESHOLD_SCHEMA` is a jsonschema used to validate `MealPlan.thresholds`.

When adding a new nutrient: add a field to `Food`, add it to `NUTRIENTS`, add matching `_min`/`_max` fields to `ThresholdPreset`, and create a migration.

---

## API Endpoints

All endpoints require authentication (`IsAuthenticated`). The API uses DRF's `DefaultRouter` mounted at `/api/`.

| Endpoint | ViewSet | Notes |
|---|---|---|
| `/api/foods/` | `FoodViewSet` | Search via `?search=`; full CRUD for custom foods; `data_source` field in responses |
| `/api/mealplans/` | `MealPlanViewSet` | Nested days filtered to `removed=False` |
| `/api/mealplan-days/` | `MealPlanDayViewSet` | Queryset pre-filtered to `removed=False` |
| `/api/mealplan-foods/` | `MealPlanFoodViewSet` | Full CRUD; auto-creates aliases from `export_name` |
| `/api/threshold-presets/` | `ThresholdPresetViewSet` | Full CRUD |
| `/api/food-aliases/` | `FoodAliasViewSet` | GET/POST/DELETE for `FoodAlias` records; filter by food with `?food=<id>` |
| `/api/export-jobs/` | `ExportJobViewSet` | POST to create async PDF export job; GET to poll status; GET `.../result/` to download PDF |

Default page size is 100. `FoodViewSet` disables pagination (`pagination_class = None`).

### Custom food management
`FoodViewSet` supports full CRUD for user-created foods:

- **Create** (`POST /api/foods/`) — generates a unique BLS code prefixed `custom_<hex>` and sets `data_source='custom'`.
- **Update** (`PUT`/`PATCH /api/foods/<id>/`) — only allowed when `data_source == 'custom'`; returns 403 for BLS-imported foods.
- **Delete** (`DELETE /api/foods/<id>/`) — only allowed for `data_source == 'custom'`; returns 403 for BLS-imported foods.

### Energy field auto-sync
`FoodSerializer` enforces that only one of `energy_in_kcal_per_100g` or `energy_in_kj_per_100g` can be set in a single request. Providing one automatically computes the other using the factor **4.184 kJ/kcal**. Supplying both fields simultaneously returns 400 Bad Request.

### Food search semantics
The food search (`?search=`) supports intent detection and multi-source matching:

1. **Energy intent** — strips energy keywords and reorders results:
   - `"low energy"` / `"low cal"` / `"low kcal"` / `"low kj"` → sorts by lowest `energy_in_kcal_per_100g`
   - `"high cal"` / etc. → sorts by highest energy

2. **Name/BLS code matching** — remaining terms are matched against `name` and `bls_code` with relevance ranking (exact → prefix → word-boundary → default).

3. **Umlaut-tolerant matching** — queries automatically generate all substitution variants for German umlauts (ä↔a, ö↔o, ü↔u). Handles both user-typed-with-umlaut and user-typed-without-umlaut cases. For up to 6 substitutable positions, all 2^n−1 combinations are searched; for more positions, single substitutions are used as a fallback.

4. **Alias matching** — after name-based results are gathered, the cached `FoodAlias` index is checked. Foods that match only via alias appear after name-matched foods and carry a non-null `matched_alias` field in the serialized response.

### Auto-alias creation
When a `MealPlanFood` is created or updated with a non-empty `export_name`, the system checks whether that name is already findable via food search (name or alias). If not, it automatically creates a `FoodAlias` linking the `export_name` to the food and invalidates the alias cache.

### Food alias management
`FoodAliasViewSet` provides direct CRUD for alias records (used by the food editor UI):

- **List** (`GET /api/food-aliases/?food=<id>`) — returns aliases for a specific food.
- **Create** (`POST /api/food-aliases/`) — creates an alias; uses `get_or_create` so duplicate POSTs are idempotent.
- **Delete** (`DELETE /api/food-aliases/<id>/`) — removes an alias and the cache is invalidated via signal.
- `PUT`/`PATCH` are not supported (aliases are atomic: delete and re-create to rename).

### Async PDF Export (`/api/export-jobs/`)
PDF generation runs as a Celery background task. The frontend polls for completion.

**Workflow:**
1. **POST `/api/export-jobs/`** — body: `{ "meal_plan_id": <int> }`. Creates a `BackgroundJob` (status=PENDING, expires in 24h), dispatches `generate_pdf_task` via Celery, returns 201 with `BackgroundJobSerializer`.
2. **GET `/api/export-jobs/<id>/`** — poll for status/progress. Returns `{ id, status, progress, error_message, created_at, updated_at }`.
3. **GET `/api/export-jobs/<id>/result/`** — available once `status=DONE`. Returns PDF as `FileResponse` with `Content-Disposition: attachment`.

**Serializers:**
- `BackgroundJobCreateSerializer` — input only, validates `meal_plan_id`
- `BackgroundJobSerializer` — read-only output for polling

**`generate_pdf_task`** (in `meals/tasks.py`):
- Celery shared task; soft limit 300s / hard limit 360s
- Activates the user's language (`activate(language)`) for translated strings
- Progress milestones: 0% → RUNNING, 25% → context loaded, 60% → HTML rendered, 90% → PDF bytes generated, 100% → DONE
- Resolves static/media file URLs via `django_url_fetcher` (no HTTP context in worker)
- Saves PDF to `exports/` via `BackgroundJob.result_file`; status → DONE on success, FAILED on error

**`django_url_fetcher(url, **kwargs)`** (in `meals/views.py`):
- Custom WeasyPrint URL fetcher used by both the sync view and the Celery task
- Maps `STATIC_URL` → `STATIC_ROOT` / `finders.find()`; maps `MEDIA_URL` → `MEDIA_ROOT`; falls back to `weasyprint.default_url_fetcher`

**Synchronous fallback:** `meal_plan_pdf(request, pk)` still exists for direct/browser download.

---

## Frontend URLs

| URL | View | Name |
|---|---|---|
| `/` | `meal_plan_list` | `meal-plan-list` |
| `/meal-plan/new/` | `meal_plan_detail` (pk=None) | `meal-plan-create` |
| `/meal-plan/<pk>/` | `meal_plan_detail` | `meal-plan-detail` |
| `/meal-plan/<pk>/pdf/` | `meal_plan_pdf` | `meal-plan-pdf` |
| `/meal-plan/<pk>/preview/` | `meal_plan_preview` | `meal-plan-preview` |
| `/meal-plan/<pk>/preview/content/` | `meal_plan_preview_content` | `meal-plan-preview-content` |
| `/search/` | `index` | `food-search` |
| `/foods/` | `food_database` | `food-database` |
| `/foods/<pk>/` | `food_editor` | `food-editor` |
| `/login/` | Django auth | `login` |
| `/logout/` | Django auth | `logout` |

All frontend views require login (`@login_required`). Creating a meal plan at `/meal-plan/new/` auto-creates a `MealPlanDay` (named "Day 1") and redirects to the new plan's detail page.

The `meal_plan_preview_content` view has `@xframe_options_sameorigin` to allow embedding in the preview iframe.

---

## Templates

Templates use the `.html.j2` extension and are processed by Django's standard template engine (not Jinja2, despite the extension). They inherit from `base.html.j2`.

| Template | Purpose |
|---|---|
| `base.html.j2` | Base layout |
| `login.html.j2` | Login page |
| `mealplan_list.html.j2` | List with search and pagination |
| `mealplan_detail.html.j2` | Detail/edit view |
| `mealplan_pdf.html.j2` | PDF content (also used for preview) |
| `mealplan_preview.html.j2` | Preview wrapper (iframe) |
| `index.html.j2` | Food search page |
| `food_database.html.j2` | Food database browser (list + search) |
| `food_editor.html.j2` | Food editor for creating/editing custom foods |

Custom template filters (`meals/templatetags/meal_extras.py`):
- `divide_by_100_mult(value, arg)` — `(value / 100) * arg` (nutrient calculation per amount)
- `split_to_dict(value)` — splits `"key:val,key2:val2"` into list of pairs
- `get_item(dictionary, key)` — safe dict lookup
- `get_attr(obj, attr_name)` — safe attribute access on an object

---

## Vue Frontend

The meal plan list page uses a Vue 3 / Vite SPA. Source lives in `frontend/src/mealplan-list/`.

**JS package manager**: `pnpm` (never `npm` or `yarn`). Lock file: `pnpm-lock.yaml` in repo root.

```bash
pnpm install          # install dependencies
pnpm dev              # start Vite dev server at :5173
pnpm build            # build to frontend/dist/
```

`django-vite` 3.x bridges Vite and Django:
- `DEBUG=True`: proxies asset requests to Vite dev server
- `DEBUG=False`: reads `frontend/dist/.vite/manifest.json` for hashed asset URLs

### Vue Component Tree (`frontend/src/mealplan-list/`)

- `main.js` — mounts `MealPlanApp` on `#meal-plan-app`; provides csrfToken, i18n, createUrl
- `MealPlanApp.vue` — fetches all plans via API (follows DRF `next` pagination); client-side filter + pagination (10/page); URL sync via `pushState`
- `SearchBar.vue` — 300ms debounced search; `id="liveSearch"` for Playwright tests
- `MealPlanTable.vue` — table of plans
- `MealPlanRow.vue` — individual plan row
- `DayBadge.vue` — day count badge
- `Pagination.vue` — page navigation
- `ConfirmDeleteModal.vue` — confirmation dialog for plan deletion

### Vue Component Tree (`frontend/src/food-database/`)

- `main.js` — mounts `FoodDatabaseApp` on its mount element; provides csrfToken and API URL
- `FoodDatabaseApp.vue` — lists all foods with search and pagination; delegates to child components
- `FoodSearchBar.vue` — debounced search input
- `FoodTable.vue` — tabular food listing
- `FoodRow.vue` — individual food row (links to food editor)
- `Pagination.vue` — page navigation

### Vue Component Tree (`frontend/src/food-editor/`)

- `main.js` — mounts `FoodEditorApp` for creating and editing a single custom food
- `FoodEditorApp.vue` — form with all nutrient fields; calls `POST`/`PUT` on `/api/foods/`; enforces `data_source == 'custom'` edit rules; includes an **Aliases** section (available for all foods, BLS and custom) that calls `/api/food-aliases/` to list, add, and delete aliases

### Vue Component Tree (`frontend/src/mealplan-detail/`)

The meal plan detail page is a full Vue 3 SPA. Source lives in `frontend/src/mealplan-detail/`.

- `main.js` — mounts `MealPlanDetailApp` on `#meal-plan-detail-app`; provides `planId`, `csrfToken`, `nutrients`, `i18n`, `pdfUrl`, `previewUrl`, `planListUrl`
- `components/MealPlanDetailApp.vue` — root component; orchestrates the detail page
- `components/PageHeader.vue` — plan name/subtitle editing, navigation back to list
- `components/Toolbar.vue` — top action bar (add day, export PDF, etc.)
- `components/StickyBar.vue` — nutrient summary bar that sticks to the viewport
- `components/PlanOverview.vue` — nutrient totals overview across all days
- `components/DaySection.vue` — one day's card with meals and foods
- `components/DaySidePanel.vue` — side panel showing nutrients for a single day
- `components/MealSection.vue` — breakfast/lunch/dinner section within a day
- `components/IngredientRow.vue` — a single food entry with amount and meal type
- `components/FoodSearchDropdown.vue` — autocomplete search dropdown for adding foods
- `components/SavePresetModal.vue` — dialog for saving current thresholds as a preset
- `components/ConfirmDeleteDayModal.vue` — confirmation dialog for day deletion
- `components/ConfirmDeleteIngredientModal.vue` — confirmation dialog for ingredient removal

i18n strings are passed via the `data-i18n` attribute on the mount element (Django renders translations server-side).

---

## SCSS / Static Assets

SCSS source files live in `meals/static/meals/scss/`. There are entry-point files (compiled) and partials (prefixed with `_`, imported by entry points).

| File | Purpose |
|---|---|
| `main.scss` | Main entry point |
| `mealplan_detail.scss` | Detail page styles |
| `mealplan_list.scss` | List page styles |
| `mealplan_preview.scss` | Preview page styles |
| `pdf.scss` | PDF/print styles |
| `food_search.scss` | Food search page styles |
| `food_database.scss` | Food database browser styles |
| `food_editor.scss` | Food editor page styles |
| `login.scss` | Login page styles |
| `_layout.scss` | Shared layout partials |
| `_reset.scss` | CSS reset partial |
| `_variables.scss` | SCSS variables partial |

**Development**: The `{% sass_src %}` template tag compiles SCSS on demand via `django-sass-processor`. No manual compilation needed.

**Deployment/CI**: Run `uv run python manage.py build_scss` before `collectstatic`. This compiles all entry-point SCSS files to `sass_cache/` using `libsass`. Then `collectstatic` copies CSS to `STATIC_ROOT`.

```bash
uv run python manage.py build_scss           # compile SCSS → sass_cache/
uv run python manage.py collectstatic        # copy to staticfiles/
```

`SASS_PROCESSOR_ROOT` is set to `BASE_DIR / 'sass_cache'` and is listed in `STATICFILES_DIRS` so compiled CSS is picked up by `collectstatic`.

---

## Internationalization (i18n)

The application supports English and German via Django's i18n framework.

- `USE_I18N = True`, `LANGUAGE_CODE = 'en'`
- `LocaleMiddleware` is active (between `SessionMiddleware` and `CommonMiddleware`)
- Translation files: `meals/locale/de/LC_MESSAGES/django.po` and `en/`
- Context processor: `django.template.context_processors.i18n`
- Nutrient labels in `nutrients.py` use `gettext_lazy(_(...))` for translation
- User-facing strings in views use `gettext` (`_(...)`); default names like `"New Plan"` / `"Day 1"` are translated at request time

---

## Environment Variables

Copy `.env.example` to `.env` before running locally:

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key |
| `DEBUG` | No | Default `False` |
| `ALLOWED_HOSTS` | No | Comma-separated; defaults to `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | No | Comma-separated HTTPS origins |
| `DATABASE_URL` | No | Default: `sqlite:///db.sqlite3`; prod: `postgres://…` |
| `CELERY_BROKER_URL` | No | Default: `redis://localhost:6379/0`; broker for Celery tasks |
| `REDIS_URL` | No | Default: `redis://localhost:6379/1`; Django cache backend |
| `SITE_BASE_URL` | No | Default: `http://localhost:8000`; base URL used by the Celery worker to resolve static/media files (no HTTP request context available in worker) |

Proxy headers (`X-Forwarded-Proto`, `X-Forwarded-Host`, `X-Forwarded-Port`) are trusted for reverse-proxy deployments.

---

## Celery / Redis

Async task processing uses **Celery** backed by **Redis**.

### Configuration (`config/celery.py` + `config/settings.py`)

```python
CELERY_BROKER_URL      = "redis://localhost:6379/0"   # task broker
CELERY_RESULT_BACKEND  = None                          # BackgroundJob is source of truth
CELERY_TASK_SERIALIZER = "json"
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 200_000           # 200 MB
CELERY_TIMEZONE = "UTC"
```

Redis also serves as Django's **cache backend** on DB 1 (separate from the broker on DB 0).

### Running the worker locally

```bash
uv run celery -A config worker -l info
```

### Tasks (`meals/tasks.py`)

| Task | Purpose |
|---|---|
| `generate_pdf_task` | Async PDF generation; updates `BackgroundJob.status`/`progress`; saves result to `exports/` |

### K8s / Docker Compose

In the Kubernetes deployment a Celery **worker sidecar container** runs alongside the Django container in the same pod (shares the `staticfiles` volume so `django_url_fetcher` can resolve static assets). The Docker Compose stack adds a separate `worker` service.

---

## Food Data Import

The BLS Excel file can be imported with:

```bash
uv run python manage.py import_foods <path/to/bls_file.xlsx>
```

The command uses `openpyxl` with hard-coded BLS column mappings (e.g. column A = BLS code, B = name, D = kJ, G = kcal, etc.) and performs `update_or_create` by `bls_code`.

---

## Key Conventions

- **Python formatting**: `black` is the code formatter. Run `uv run black .` to format; CI enforces `uv run black --check .`. Always format before committing Python changes.
- **Soft deletes**: `MealPlanDay.removed` — never hard-delete days; set `removed=True` instead. Always filter with `removed=False` in queries.
- **Nutrient keys**: Use the exact string keys from `NUTRIENT_IDS` (e.g. `"protein_in_g"`, not `"protein"`). The `MealPlan.clean()` method migrates old key names on save.
- **Model validation**: `MealPlan.save()` always calls `full_clean()`. Do not bypass validation with `update()` if you need thresholds/nutrient integrity.
- **PDF generation**: WeasyPrint requires system libraries (libpango, libcairo, etc.). The Dockerfile installs these. For local dev, ensure they are installed on the host. See CI workflow for the exact apt packages.
- **Templates**: Use `.html.j2` extension. Load `meal_extras` tags where nutrient calculations are needed.
- **Default names are German**: `"Neuer Plan"`, `"Neuer Tag"`, meal type labels (`Frühstück`, `Mittagessen`, `Abendessen`) — but views use `_()` so these are translated at request time.
- **Alias cache**: Do not call `FoodAlias.objects.filter(...)` in hot paths; use `get_alias_index()` instead. The cache is a `dict[food_id → list[alias_string]]` stored under the key `food_aliases_index`. It is invalidated automatically by signals on save/delete of `FoodAlias` rows.
- **SiteSettings singleton**: Always access via `SiteSettings.get()`, never `SiteSettings.objects.get(pk=1)` directly.
- **`export_name` on `MealPlanFood`**: Setting this field triggers automatic alias creation if the name is not already findable by search. This side-effect happens in `MealPlanFoodViewSet.perform_create/perform_update`.
- **Custom foods**: Foods with `data_source='custom'` are user-created. BLS-imported foods have `data_source=''`. Only custom foods can be edited or deleted via the API. Custom BLS codes are auto-generated as `custom_<hex>`.
- **Energy sync**: When creating or updating a food via the API, supply either `energy_in_kcal_per_100g` or `energy_in_kj_per_100g` — not both. The serializer automatically computes the missing value using 4.184 kJ/kcal.
- **BackgroundJob as task state**: `BackgroundJob` is the sole source of truth for Celery task progress/results. `CELERY_RESULT_BACKEND` is intentionally `None`. Poll via `/api/export-jobs/<id>/`.
- **PDF worker URL resolution**: The Celery worker has no HTTP request context. Static and media files are resolved by `django_url_fetcher` using filesystem paths. Always set `SITE_BASE_URL` in production so the worker can build absolute URLs when needed.
- **PDF footer**: `SiteSettings.pdf_footer_line_content` controls the footer text on every PDF page. Access the setting via `SiteSettings.get()`.
- **Migrations**: When adding models or fields, always create and commit migrations. Latest is `0027_food_water_in_g_per_100g`.

---

## Admin

All models are registered in `meals/admin.py`:

| Model | Admin class | Notable features |
|---|---|---|
| `Food` | `FoodAdmin` | Inline `FoodAlias` editing; search on name/bls_code |
| `FoodAlias` | `FoodAliasAdmin` | `raw_id_fields` for food lookup |
| `MealPlan` | `MealPlanAdmin` | Inline `MealPlanDay` |
| `MealPlanDay` | `MealPlanDayAdmin` | Inline `MealPlanFood` |
| `ThresholdPreset` | `ThresholdPresetAdmin` | Search on name |
| `SiteSettings` | `SiteSettingsAdmin` | List view redirects to single instance; add/delete disabled |

---

## Deployment

### Docker

```bash
docker compose up --build
```

The Dockerfile uses a **three-stage build**:

1. **node-builder** (`node:22-slim`): installs JS deps with `pnpm install --frozen-lockfile` and builds the Vue frontend (`pnpm build`).
2. **builder** (`ghcr.io/astral-sh/uv:python3.12-bookworm-slim`): installs Python dependencies via `uv sync --frozen --no-install-project --no-dev`.
3. **final** (`python:3.12-slim-bookworm`): copies the venv from builder and the built JS assets from node-builder; installs WeasyPrint system libraries (`libglib2.0-0`, `libpango-1.0-0`, `libharfbuzz0b`, `libpangoft2-1.0-0`, `libpangocairo-1.0-0`, `libcairo2`, `libgdk-pixbuf2.0-0`); exposes port 8000; starts gunicorn.

### Kubernetes (via Ansible)

The project targets a **k3s** cluster. Infrastructure is split into two areas:

```
deployment/
├── bootstrap/           # One-time cluster infrastructure setup
│   ├── ansible/         # bootstrap.yml playbook + Jinja2 secret templates
│   └── k8s/
│       ├── base/        # PVC (1 Gi media), StorageClass (local-path-retain)
│       └── overlays/dev/  # Namespace, CNPG Postgres cluster, secretGenerator
└── app-deployment/      # Application deployment (built + pushed on every release)
    ├── ansible/         # deploy.yml playbook + vars.yml
    └── k8s/
        ├── base/        # Deployment, Service, Redis, ConfigMap
        └── overlays/dev/  # Ingress (TLS), image tag, resource limits
```

#### Bootstrap (run once per environment)

```bash
cd deployment/bootstrap/ansible
uv run ansible-playbook --vault-id ${ANSIBLE_VAULT_ID}@vault-key-client bootstrap.yml
```

The bootstrap playbook renders Jinja2 secret templates (database credentials, Django `SECRET_KEY`, superuser credentials) from Ansible Vault into `k8s/overlays/dev/*.env` files (mode `0600`), then applies the kustomize overlay to create the namespace, PVC, StorageClass, and a **CloudNativePG (CNPG)** Postgres cluster (1 replica, 2 Gi `local-path-retain` storage).

The CNPG service endpoint exposed to the app is `meal-plan-analyzer-db-rw:5432`.

#### Application deployment

```bash
cd deployment/app-deployment/ansible
uv run ansible-playbook --vault-id ${ANSIBLE_VAULT_ID}@vault-key-client deploy.yml -e env=dev
```

The deploy playbook builds and pushes the Docker image to DockerHub, then applies `k8s/overlays/{env}/` via `kubectl apply -k` and triggers a rolling restart (`kubectl rollout restart`).

#### K8s pod init-container chain

When the app pod starts, five **init containers** run in sequence before the main containers:

| Init container | Command |
|---|---|
| `build-scss` | `python manage.py build_scss` |
| `collect-static` | `python manage.py collectstatic --noinput` |
| `migrate` | `python manage.py migrate` |
| `create-superuser` | Python shell — idempotent superuser creation |
| `import-foods` | `python manage.py import_foods` (downloads BLS ZIP) |

After init, two **app containers** run in the same pod:
- `meal-plan-analyzer` — gunicorn on port 8000; liveness/readiness probes configured
- `worker` — Celery sidecar; shares the `staticfiles` and `media` volumes so `django_url_fetcher` can resolve assets without HTTP

**Shared volumes**: `staticfiles` (emptyDir), `sass-cache` (emptyDir), `media` (PVC — `meal-plan-analyzer-media-pvc`).

#### Environments

| Environment | Namespace | Image tag | Ingress |
|---|---|---|---|
| dev | `meal-plan-analyzer-dev` | `dev` | `mealplananalyzer-dev.saadeh.dev` (LetsEncrypt DNS TLS) |
| prod | `meal-plan-analyzer` | `latest` | (not in repo) |

Resource limits for dev: 500m CPU / 512 Mi memory.

#### Secrets management

- Secrets are stored in an **Ansible Vault** (`vault.yml`); decrypt with `vault-key-client`.
- The bootstrap playbook renders them into `.env` files and passes them to `kustomize secretGenerator` (`disableNameSuffixHash: true`).
- Three K8s Secrets are created: `meal-plan-analyzer-secret` (DATABASE_URL, SECRET_KEY), `meal-plan-analyzer-db-credentials` (CNPG credentials), `meal-plan-analyzer-superuser-secret`.
- GitHub Actions secrets required: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `KUBECONFIG` (base64-encoded), optional `DOCKERHUB_REPO`.

### CI/CD (GitHub Actions)

Workflows live in `.github/workflows/`:

| Workflow | Trigger | Purpose |
|---|---|---|
| `tests.yml` | PRs to `main` | Lint (Black) + Unit/Integration + API + Playwright frontend tests; JUnit XML reports via `dorny/test-reporter`; failure artifacts (screenshots + traces, 7-day retention) |
| `deploy-dev.yml` | Push to `main` | Builds Docker image tagged `dev` with `APP_VERSION=dev-{branch}-{sha}`, pushes to DockerHub, applies dev K8s overlay, triggers rollout restart |
| `release.yml` | Push to `v*` tags | Builds and pushes image tagged `{tag}` and `latest`; `APP_VERSION={tag}` |
| `security-audit.yml` | PRs to `main`, weekly Monday 03:00 UTC, manual | `pip-audit` (CycloneDX SBOM + JSON) + `pnpm audit`; fails on high/critical JS vulns; uploads artifacts (90-day retention) |
| `pages.yml` | Push/PR to `main` | Deploys `./docs/` to GitHub Pages |

All test jobs install WeasyPrint system dependencies via apt before running tests. A **Test Summary** job writes a Markdown table to the workflow summary on every run.

---

## Testing Conventions

- API tests (`tests/api/`) use `@pytest.mark.django_db` and the `authenticated_client` / `api_client` fixtures. Includes `test_food_aliases.py` for the `/api/food-aliases/` endpoint.
- Frontend tests (`tests/frontend/`) use the `logged_in_page` fixture (Playwright `Page` already logged in). Includes `test_food_editor.py` for the food editor aliases UI.
- Top-level tests (`tests/test_*.py`) cover models, views, admin, nutrients, template filters, search utilities, PDF views, and food import.
- Factory definitions for test objects are in `tests/frontend/factories.py` (`FoodFactory`, `MealPlanFactory`, `MealPlanDayFactory`, `MealPlanFoodFactory`).
- Test food data is loaded from `tests/data/food_fixtures.json` once per session.
- `tests/conftest.py` provides: `api_client`, `user`, `authenticated_client`; also disables `CompressedManifestStaticFilesStorage` for tests.
- Use `--create-db` flag to rebuild the test database if migrations change.

### CI (GitHub Actions)

Four jobs in `.github/workflows/tests.yml` run on pull requests to `main`:

- **Lint (Black)**: `uv run black --check .` — enforces consistent Python formatting.
- **Unit & Integration Tests**: builds JS (`pnpm build`), compiles SCSS, then runs `uv run pytest tests/test_*.py --create-db`.
- **API Tests**: builds JS, then runs `uv run pytest tests/api/ --create-db`.
- **Frontend Tests (Playwright)**: builds JS, compiles SCSS, installs Playwright Chromium, then runs `uv run pytest tests/frontend/ --create-db --screenshot=only-on-failure --tracing=retain-on-failure`. Playwright failure artifacts (screenshots + traces) are uploaded on failure.

All test jobs install WeasyPrint system dependencies via apt before running. Test results are published via `dorny/test-reporter` as JUnit XML to the GitHub Checks tab. A final **Test Summary** job writes a Markdown table to the workflow summary.
