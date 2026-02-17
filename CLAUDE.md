# CLAUDE.md — AI Assistant Guide for RSOS Meal Planner

## Project Overview

RSOS Meal Planner is a Django web application for meal planning and nutritional analysis. Food data is sourced from the **Bundes Lebensmittel Schlüssel (BLS)** — the German national food composition database. Users can create meal plans, assign foods to daily meals, track nutrient totals against configurable thresholds, and export plans as PDFs.

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

The compose stack spins up a PostgreSQL 16 container and the Django app on port 8000. Migrations and `collectstatic` run automatically on startup.

---

## Running Tests

```bash
uv run pytest              # full suite (API + frontend)
uv run pytest tests/api/   # API tests only
uv run pytest tests/frontend/  # Playwright browser tests only
```

`pytest.ini` sets:
- `DJANGO_SETTINGS_MODULE = config.settings`
- `--reuse-db` (the test database is reused across runs; use `--create-db` to force rebuild)

The session-scoped `django_db_setup` fixture in `tests/conftest.py` auto-loads `tests/data/food_fixtures.json`.

Frontend tests use **Playwright** (`pytest-playwright`). They require a running live server (pytest-django's `live_server` fixture handles this automatically).

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
│   ├── templatetags/
│   │   └── meal_extras.py   # Custom template filters
│   ├── templates/meals/     # Jinja2-style .html.j2 templates
│   ├── static/meals/img/    # Static assets (logo, etc.)
│   ├── migrations/          # Django migrations (0001–0017)
│   └── management/commands/
│       └── import_foods.py  # BLS Excel import command
│
├── tests/
│   ├── conftest.py          # Shared fixtures (api_client, user, authenticated_client)
│   ├── data/
│   │   └── food_fixtures.json  # Seed data for tests
│   ├── api/
│   │   ├── test_foods.py
│   │   ├── test_mealplans.py
│   │   └── test_mealplandays.py
│   └── frontend/
│       ├── conftest.py      # Playwright fixtures (logged_in_page)
│       ├── factories.py     # factory-boy factories
│       ├── test_mealplan_list.py
│       ├── test_mealplan_detail.py
│       └── test_pdf.py
│
├── ansible/                 # Deployment playbooks for k3s
├── k8s/                     # Kubernetes manifests
├── pyproject.toml           # Project metadata and dependencies
├── pytest.ini
├── Dockerfile               # Multi-stage build (builder → python:3.12-slim)
├── docker-compose.yml
├── .env.example             # Environment variable template
├── .python-version          # Python 3.12
└── .agent/                  # AI agent rules and workflows
    ├── rules/
    │   ├── backend-package-manager.md
    │   └── running-backend-tests.md
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
| `protein_in_g_per_100g` | FloatField | |
| `fat_in_g_per_100g` | FloatField | |
| `carbohydrate_in_g_per_100g` | FloatField | |
| `fibre_in_g_per_100g` | FloatField | |
| `iron_in_mg_per_100g` | FloatField | |
| `sugar_in_g_per_100g` | FloatField | |
| `omega3_in_g_per_100g` | FloatField | |
| `vitc_in_mg_per_100g` | FloatField | Vitamin C |
| `magnesium_in_mg_per_100g` | FloatField | |
| `zinc_in_mg_per_100g` | FloatField | |
| `vitb12_in_mug_per_100g` | FloatField | Vitamin B12 (µg) |
| `vita_in_mug_per_100g` | FloatField | Vitamin A (µg) |
| `calcium_in_mg_per_100g` | FloatField | |
| `vitd_in_mug_per_100g` | FloatField | Vitamin D (µg) |

### `MealPlan`
A named collection of days.

- `name` — default `"Neuer Plan"`
- `creation_date` / `change_date` — auto timestamps
- `visible_nutrients` — JSON list of nutrient keys (defaults to all); validated against `NUTRIENT_IDS`
- `thresholds` — JSON dict `{ nutrient_key: { "min": float|null, "max": float|null } }`; validated by `THRESHOLD_SCHEMA`
- `clean()` migrates legacy nutrient key names automatically (e.g. `protein` → `protein_in_g`)
- `save()` calls `full_clean()` — model-level validation always runs on save

### `MealPlanDay`
One day within a meal plan.

- `name` — default `"Neuer Tag"`
- `meal_plan` — FK → `MealPlan` (nullable)
- `foods` — M2M → `Food` via `MealPlanFood`
- `removed` — soft-delete flag (default `False`); active days are always filtered with `removed=False`

### `MealPlanFood`
Junction table between `MealPlanDay` and `Food`.

- `amount_in_g` — FloatField
- `meal_type` — choices: `breakfast`, `lunch`, `dinner`
- Unique constraint: `(meal_plan_day, food, meal_type)`

### `ThresholdPreset`
Reusable named threshold presets. Has `_min` / `_max` FloatField pairs for every nutrient tracked in `NUTRIENTS`.

---

## Nutrients (`meals/nutrients.py`)

All nutrient logic flows through the `NUTRIENTS` ordered dict. Each entry maps a **nutrient key** to its label, unit, and the corresponding `Food` model field (`food_key`).

| Nutrient key | Label | Unit |
|---|---|---|
| `energy_in_kcal` | Energie | kcal |
| `protein_in_g` | Protein | g |
| `fat_in_g` | Fett | g |
| `omega3_in_g` | O3 | g |
| `carbohydrate_in_g` | KH | g |
| `sugar_in_g` | Zucker | g |
| `fibre_in_g` | Bst. | g |
| `iron_in_mg` | Eisen | mg |
| `vitc_in_mg` | Vit. C | mg |
| `magnesium_in_mg` | Mg | mg |
| `zinc_in_mg` | Zink | mg |
| `vitb12_in_mug` | Vit. B12 | µg |
| `vita_in_mug` | Vit. A | µg |
| `calcium_in_mg` | Ca | mg |
| `vitd_in_mug` | Vit. D | µg |

`NUTRIENT_IDS` is the list of all keys. `THRESHOLD_SCHEMA` is a jsonschema used to validate `MealPlan.thresholds`.

When adding a new nutrient: add a field to `Food`, add it to `NUTRIENTS`, add matching `_min`/`_max` fields to `ThresholdPreset`, and create a migration.

---

## API Endpoints

All endpoints require authentication (`IsAuthenticated`). The API uses DRF's `DefaultRouter` mounted at `/api/`.

| Endpoint | ViewSet | Notes |
|---|---|---|
| `/api/foods/` | `FoodViewSet` | Search via `?search=` with semantic intent parsing |
| `/api/mealplans/` | `MealPlanViewSet` | Nested days filtered to `removed=False` |
| `/api/mealplan-days/` | `MealPlanDayViewSet` | Queryset pre-filtered to `removed=False` |
| `/api/mealplan-foods/` | `MealPlanFoodViewSet` | Full CRUD |
| `/api/threshold-presets/` | `ThresholdPresetViewSet` | Full CRUD |

Default page size is 100. `FoodViewSet` disables pagination (`pagination_class = None`).

### Food search semantics
The food search (`?search=`) supports intent detection:
- `"low energy"` / `"low cal"` → sorts by lowest `energy_in_kcal_per_100g`
- `"high cal"` → sorts by highest energy
- Remaining terms are matched against `name` and `bls_code` with relevance ranking

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
| `/login/` | Django auth | `login` |
| `/logout/` | Django auth | `logout` |

All frontend views require login (`@login_required`). Creating a meal plan at `/meal-plan/new/` auto-creates a `MealPlanDay` and redirects to the new plan's detail page.

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

Custom template filters (`meals/templatetags/meal_extras.py`):
- `divide_by_100_mult(value, arg)` — `(value / 100) * arg` (nutrient calculation per amount)
- `split_to_dict(value)` — splits `"key:val,key2:val2"` into list of pairs
- `get_item(dictionary, key)` — safe dict lookup

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

Proxy headers (`X-Forwarded-Proto`, `X-Forwarded-Host`, `X-Forwarded-Port`) are trusted for reverse-proxy deployments.

---

## Food Data Import

The BLS Excel file can be imported with:

```bash
uv run python manage.py import_foods <path/to/bls_file.xlsx>
```

The command uses `openpyxl` with hard-coded BLS column mappings (e.g. column A = BLS code, B = name, D = kJ, G = kcal, etc.) and performs `update_or_create` by `bls_code`.

---

## Key Conventions

- **Soft deletes**: `MealPlanDay.removed` — never hard-delete days; set `removed=True` instead. Always filter with `removed=False` in queries.
- **Nutrient keys**: Use the exact string keys from `NUTRIENT_IDS` (e.g. `"protein_in_g"`, not `"protein"`). The `MealPlan.clean()` method migrates old key names on save.
- **Model validation**: `MealPlan.save()` always calls `full_clean()`. Do not bypass validation with `update()` if you need thresholds/nutrient integrity.
- **PDF generation**: WeasyPrint requires system libraries (libpango, libcairo, etc.). The Dockerfile installs these. For local dev, ensure they are installed on the host.
- **Templates**: Use `.html.j2` extension. Load `meal_extras` tags where nutrient calculations are needed.
- **Default names are German**: `"Neuer Plan"`, `"Neuer Tag"`, meal type labels (`Frühstück`, `Mittagessen`, `Abendessen`). Keep user-facing strings in German.

---

## Deployment

### Docker

```bash
docker compose up --build
```

### Kubernetes (via Ansible)

```bash
cd ansible
uv run ansible-playbook --vault-id saadeh.devk3s@vault-key-client deploy.yml
```

Manifests live in `k8s/`. The Ansible playbook handles DNS, database, and app deployment to a k3s cluster.

---

## Testing Conventions

- API tests use `@pytest.mark.django_db` and the `authenticated_client` / `api_client` fixtures.
- Frontend tests use the `logged_in_page` fixture (Playwright `Page` already logged in).
- Factory definitions for test objects are in `tests/frontend/factories.py`.
- Test food data is loaded from `tests/data/food_fixtures.json` once per session.
- Use `--create-db` flag to rebuild the test database if migrations change.
