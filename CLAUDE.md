# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

RSOS Meal Planner — a Django 6.0 + Vue 3 web app for meal planning and nutritional analysis. Food data comes from the **Bundes Lebensmittel Schlüssel (BLS)**, the German national food composition database. Users build multi-day meal plans, track nutrient totals against threshold presets, and export plans as PDFs (async via Celery).

## Package Managers (mandatory)

- **Python: `uv`** — never `pip` or bare `python`. Always prefix Python commands with `uv run`. `uv.lock` and `pyproject.toml` must stay in sync.
- **JS: `pnpm`** — never `npm` or `yarn`. Lock file `pnpm-lock.yaml` lives at repo root.

## Common Commands

```bash
# Setup
uv sync
cp .env.example .env                                  # set SECRET_KEY at minimum
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver

# Frontend
pnpm install
pnpm dev                                              # Vite dev server :5173
pnpm build                                            # production build → frontend/dist/
pnpm type-check                                       # vue-tsc --noEmit

# Format (CI enforces — ALWAYS run before pytest)
uv run black .
uv run black --check .

# Tests
uv run black . && uv run pytest                       # full suite
uv run pytest tests/api/                              # API only
uv run pytest tests/frontend/                         # Playwright only
uv run pytest tests/test_*.py                         # unit/integration only
uv run pytest tests/api/test_foods.py::TestFoodAPI::test_x   # single test
uv run pytest -k "alias"                              # pattern match
uv run pytest --create-db                             # rebuild DB after migration changes

# First-time Playwright setup
uv run playwright install --with-deps chromium
uv run python manage.py build_scss                    # required before frontend tests

# SCSS / static
uv run python manage.py build_scss                    # compile to sass_cache/
uv run python manage.py collectstatic                 # copy to STATIC_ROOT

# Background worker (PDF export)
uv run celery -A config worker -l info

# Import BLS data
uv run python manage.py import_foods <path/to/bls_file.xlsx>
```

`pytest.ini` sets `DJANGO_SETTINGS_MODULE=config.settings` and `--reuse-db`. The session-scoped `django_db_setup` fixture in `tests/conftest.py` auto-loads `tests/data/food_fixtures.json`. There is **no JS lint/type-check step in CI** — type errors only surface on `pnpm build` or `pnpm type-check`.

## Architecture

### Layout
- `config/` — Django project (`settings.py` via django-environ, `celery.py`, root URLs).
- `meals/` — the only Django app. **`meals/views/` is a package**, split into `food.py`, `mealplan.py`, `threshold.py`. `meals/views/__init__.py` re-exports the public API.
- `frontend/src/<page>/` — one Vue 3 / TypeScript SPA per page (`mealplan-list`, `mealplan-detail`, `food-database`, `food-editor`, `threshold-preset-list`, `threshold-preset-editor`). Each has a `main.ts` entry mounted on a Django template element. Shared types in `frontend/src/types/`.
- `tests/` — split into `api/` (DRF), `frontend/` (Playwright), and top-level `test_*.py` (unit/integration).
- `deployment/` — split into `bootstrap/` (one-time cluster setup, CNPG Postgres) and `app-deployment/` (built/pushed every release). Both use Ansible + kustomize overlays for k3s.

### Vite ↔ Django bridge
`django-vite` 3.x: with `DEBUG=True` Django proxies asset requests to the Vite dev server; with `DEBUG=False` it reads `frontend/dist/.vite/manifest.json` for hashed asset URLs. Templates use the `.html.j2` extension but are processed by **Django's standard template engine** (not Jinja2).

### Data model invariants (`meals/models.py`)
- **Soft delete**: never hard-delete `MealPlanDay`; set `removed=True`. Always filter active days with `removed=False`. The `MealPlanDayViewSet` queryset is pre-filtered.
- **`MealPlan.save()` calls `full_clean()`** — model-level validation always runs. `clean()` migrates legacy nutrient key names (e.g. `protein` → `protein_in_g`).
- **Nutrient keys**: use the full canonical strings from `NUTRIENT_IDS` in `meals/nutrients.py` (e.g. `"protein_in_g"`, not `"protein"`). Adding a nutrient requires: a `Food` field, a `NUTRIENTS` entry, matching `_min`/`_max` on `ThresholdPreset`, and a migration.
- **`SiteSettings` is a singleton** — always access via `SiteSettings.get()`, never `objects.get(pk=1)`. `save()` forces `pk=1`; admin disables add/delete.
- **Custom vs BLS foods**: `data_source='custom'` foods are user-created and have `bls_code` auto-generated as `custom_<hex>`. BLS-imported foods have `data_source=''`. The API only allows update/delete of custom foods (returns 403 otherwise).

### Search & alias cache (`meals/views/food.py`)
The food search (`?search=` on `/api/foods/`) layers several behaviors:
1. **Energy intent detection** — strips `low/high cal/kcal/kj/energy` keywords and re-sorts by `energy_in_kcal_per_100g`.
2. **Name + BLS code matching** with relevance ranking (exact → prefix → word-boundary → default).
3. **Umlaut-tolerant matching** — generates substitution variants for ä↔a, ö↔o, ü↔u (full 2^n−1 expansion up to 6 positions, single-substitution fallback beyond).
4. **Alias matching** — checks `FoodAlias` via the **cached alias index** (`get_alias_index()` returns `dict[food_id → list[str]]`, key `food_aliases_index`, 1-hour TTL, invalidated by `post_save`/`post_delete` signals on `FoodAlias`). Alias-only matches sort after name matches and carry `matched_alias` in the response. **Never call `FoodAlias.objects.filter(...)` in hot paths** — use `get_alias_index()`.
5. Both browse and search return the same paginated envelope `{ count, next, previous, results }` (page size 100). `MealPlanViewSet` uses a custom paginator that adds `num_pages` and `current_page`.

### Auto-alias side effect
Setting `MealPlanFood.export_name` to a non-empty value not already findable via search auto-creates a `FoodAlias`. This happens in `MealPlanFoodViewSet.perform_create/perform_update` — be aware when reasoning about alias state.

### Energy auto-sync
`FoodSerializer` rejects requests that supply **both** `energy_in_kcal_per_100g` and `energy_in_kj_per_100g`. Supply one and the other is computed using **4.184 kJ/kcal**.

### Async PDF export
`/api/export-jobs/` (POST → 201) creates a `BackgroundJob` (UUID PK, status PENDING/RUNNING/DONE/FAILED, expires 24h) and dispatches `generate_pdf_task` (Celery shared task, soft 300s / hard 360s). Poll with GET; download with GET `.../result/`.

- **`BackgroundJob` is the sole source of truth** for task progress/result. `CELERY_RESULT_BACKEND=None` is intentional.
- **`result_file` uses `meals.storage.PrivateExportsStorage`** (saved under `exports/`, not served as public media).
- The Celery worker has **no HTTP request context**, so WeasyPrint resolves URLs via `django_url_fetcher` (in `meals/views/mealplan.py`): maps `STATIC_URL` → filesystem (`STATIC_ROOT` / `finders.find()`), `MEDIA_URL` → `MEDIA_ROOT`, falls back to `weasyprint.default_url_fetcher`. In production, set `SITE_BASE_URL` so the worker can build absolute URLs.
- A synchronous `meal_plan_pdf(request, pk)` view also exists for direct browser download.

### Celery / Redis
- Broker: Redis DB 0 (`CELERY_BROKER_URL`).
- Django cache: Redis DB 1 (`REDIS_URL`) — used for the alias cache.
- Worker is a **sidecar in the same K8s pod** sharing `staticfiles` and `media` volumes with the web container; in compose it's a separate `worker` service.

### i18n
English + German via Django's i18n framework. `LocaleMiddleware` is active. Default model strings (e.g. `"Neuer Plan"`, `"Neuer Tag"`, `Frühstück`/`Mittagessen`/`Abendessen`) are German literals, but views wrap defaults with `_()` so they translate at request time. Nutrient labels use `gettext_lazy`. PO files in `meals/locale/{de,en}/LC_MESSAGES/`.

### Templates
Custom filters in `meals/templatetags/meal_extras.py`: `divide_by_100_mult` (per-amount nutrient calc), `split_to_dict`, `get_item`, `get_attr`. Load `meal_extras` wherever nutrient calculations are templated. The `meal_plan_preview_content` view uses `@xframe_options_sameorigin` so it can be embedded in the preview iframe.

## Deployment

Three-stage Dockerfile: `node-builder` (pnpm build) → `builder` (`uv sync --frozen --no-install-project --no-dev`) → `python:3.12-slim-bookworm` final with WeasyPrint system libs (`libpango-1.0-0`, `libcairo2`, `libgdk-pixbuf2.0-0`, etc.). Gunicorn on port 8000.

K8s pod has five **init containers** running in sequence: `build-scss` → `collect-static` → `migrate` → `create-superuser` (idempotent) → `import-foods`. Then two app containers run: `meal-plan-analyzer` (gunicorn) and `worker` (Celery). Shared volumes: `staticfiles` (emptyDir), `sass-cache` (emptyDir), `media` (PVC).

CI workflows (`.github/workflows/`):
- `tests.yml` (PRs to `main`) — Black lint + unit/integration + API + Playwright in four jobs. Each installs WeasyPrint apt deps. Failure artifacts (screenshots + traces) uploaded for Playwright.
- `deploy-dev.yml` (push to `main`) — builds image tagged `dev`, applies dev overlay, restarts rollout.
- `release.yml` (`v*` tags) — builds and pushes `{tag}` + `latest`.
- `security-audit.yml` — pip-audit + pnpm audit (PRs, weekly Mon 03:00 UTC).
- `pages.yml` — deploys `./docs/` to GitHub Pages.

## Environment Variables (`.env`)

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key |
| `DEBUG` | No | Default `False` |
| `ALLOWED_HOSTS` | No | Comma-separated; defaults to `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | No | Comma-separated HTTPS origins |
| `DATABASE_URL` | No | Default `sqlite:///db.sqlite3` |
| `CELERY_BROKER_URL` | No | Default `redis://localhost:6379/0` |
| `REDIS_URL` | No | Default `redis://localhost:6379/1` (cache) |
| `SITE_BASE_URL` | No | Default `http://localhost:8000`; needed by Celery worker |

Proxy headers (`X-Forwarded-Proto`/`-Host`/`-Port`) are trusted for reverse-proxy deployments.

## Conventions worth knowing

- **Naming includes units**: model fields like `energy_in_kcal_per_100g`, `vitb12_in_mug_per_100g` (`mug` = µg).
- **Imports**: stdlib → third-party (Django, DRF) → local.
- **Auth**: frontend views use `@login_required`; all DRF endpoints require `IsAuthenticated`.
- **Migrations**: latest is `0028_backgroundjob_private_storage`. Always create + commit migrations with model changes.
- **`removed=False` filtering**: enforced everywhere `MealPlanDay` is queried — keep it that way.
