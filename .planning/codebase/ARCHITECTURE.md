# Architecture

**Analysis Date:** 2026-03-16

## Pattern Overview

**Overall:** Django monolith with a DRF REST API and Vue 3 SPA micro-frontends

**Key Characteristics:**
- Single Django app (`meals`) owns all models, views, serializers, and business logic
- Django template engine serves HTML shells that mount Vue 3 SPAs for interactive pages
- DRF REST API (`/api/`) backs all Vue SPAs; same API is consumed by both frontend and tests
- Server-rendered templates handle simple pages (PDF preview wrapper, food search shell)
- No separate backend service; PDF generation happens in-process via WeasyPrint

## Layers

**Configuration Layer:**
- Purpose: Django project bootstrap, settings, root URL routing
- Location: `config/`
- Contains: `settings.py`, `urls.py`, `wsgi.py`, `asgi.py`
- Depends on: environment variables (via `django-environ` / `.env`)
- Used by: Django runtime

**Data / Model Layer:**
- Purpose: Database schema, model validation, cache-backed helpers
- Location: `meals/models.py`, `meals/nutrients.py`
- Contains: `Food`, `FoodAlias`, `MealPlan`, `MealPlanDay`, `MealPlanFood`, `ThresholdPreset`, `SiteSettings`; `NUTRIENTS` ordered dict; `THRESHOLD_SCHEMA` jsonschema; `get_alias_index()` cache helper
- Depends on: Django ORM, Django cache backend, `jsonschema`
- Used by: views, serializers, management commands

**Serialization Layer:**
- Purpose: API request/response shape, cross-field validation, energy unit auto-conversion
- Location: `meals/serializers.py`
- Contains: `FoodSerializer`, `MealPlanSerializer`, `MealPlanDaySerializer`, `MealPlanFoodSerializer`, `ThresholdPresetSerializer`
- Depends on: models, DRF
- Used by: API ViewSets

**View / API Layer:**
- Purpose: HTTP request handling — both Django template views and DRF ViewSets
- Location: `meals/views.py`
- Contains: template views (`meal_plan_list`, `meal_plan_detail`, `meal_plan_pdf`, `food_database`, `food_editor`); ViewSets (`FoodViewSet`, `MealPlanViewSet`, `MealPlanDayViewSet`, `MealPlanFoodViewSet`, `ThresholdPresetViewSet`); food search helpers (`parse_food_search`, `get_food_search_query`, `_umlaut_search_variants`)
- Depends on: models, serializers, nutrients, Django templates, WeasyPrint
- Used by: URL router

**URL Routing Layer:**
- Purpose: Map HTTP paths to views and API endpoints
- Location: `config/urls.py` (root), `meals/urls.py` (app-level)
- Contains: admin, i18n, media routes (root); all app paths + DRF `DefaultRouter` (app-level)
- Used by: Django request dispatcher

**Template Layer:**
- Purpose: Server-rendered HTML; some pages are pure shells that mount Vue SPAs, others are fully server-rendered
- Location: `meals/templates/meals/`
- Contains: `.html.j2` files (Django template engine, not Jinja2 despite extension)
- Depends on: `meal_extras` template tags, `{% sass_src %}`, `{% vite_asset %}`

**Vue SPA Layer:**
- Purpose: Interactive client-side UI for the four main pages
- Location: `frontend/src/`
- Contains: four independent Vite entry points, each a self-contained Vue 3 app
- Depends on: DRF API at `/api/`, CSRF token from Django (injected via `data-*` attribute or `<meta>` tag), i18n strings passed via `data-i18n`
- Used by: Django templates that mount `#app` elements

**Static Asset Layer:**
- Purpose: SCSS stylesheets compiled to CSS; Vue JS bundles
- Location: `meals/static/meals/scss/` (SCSS source), `sass_cache/` (compiled CSS), `frontend/dist/` (Vite output)
- Depends on: `django-sass-processor` (on-demand dev compilation), `pnpm build` (Vite production build)

**Test Layer:**
- Purpose: Automated test suite — API tests, frontend (Playwright) tests, unit tests
- Location: `tests/`
- Depends on: `pytest-django`, `pytest-playwright`, `factory-boy`, fixtures in `tests/data/`

## Data Flow

**API-backed Vue page (e.g. meal plan detail):**
1. Browser requests `/meal-plan/<pk>/` — Django `meal_plan_detail` view runs
2. View serializes `NUTRIENTS` to JSON, builds `i18n` dict, renders `mealplan_detail.html.j2` with context
3. Template mounts `<div id="mealplan-detail-app">` with embedded JSON (nutrients, i18n, URLs) in `data-*` attributes
4. Vue SPA (`frontend/src/mealplan-detail/main.js`) boots, reads `data-*` attributes as initial config
5. Vue components call `/api/mealplan-days/`, `/api/mealplan-foods/`, `/api/threshold-presets/` via `fetch` with CSRF token
6. DRF ViewSets query the DB, serialize results, return JSON
7. Vue reactivity layer updates the DOM

**Food search (API path):**
1. Vue component sends `GET /api/foods/?search=<query>`
2. `FoodViewSet.list()` calls `parse_food_search()` for energy intent detection
3. `get_food_search_query()` builds a `Q` object with umlaut variants
4. DB query runs, results annotated with relevance score and ordered
5. `get_alias_index()` checks the cache (or rebuilds from DB); alias-only matches appended with `matched_alias` field
6. `FoodSerializer` returns JSON; Vue renders results with optional alias badge

**PDF generation:**
1. Browser requests `/meal-plan/<pk>/pdf/`
2. `meal_plan_pdf` view calls `get_meal_plan_context(pk)` — computes per-day nutrient totals, averages, threshold comparisons
3. `render_to_string("meals/mealplan_pdf.html.j2", context)` produces HTML
4. `weasyprint.HTML(...).write_pdf()` renders HTML+CSS to binary PDF using `django_url_fetcher` to resolve static/media file paths
5. `HttpResponse` with `content-type: application/pdf` returned

**Export name → alias side-effect:**
1. `MealPlanFoodViewSet.perform_create/perform_update` calls `_handle_export_name_alias(instance)`
2. Checks if `export_name` is already findable by food search (name or alias path)
3. If not found, calls `FoodAlias.objects.get_or_create(...)`
4. `post_save` signal on `FoodAlias` fires `invalidate_alias_cache()` → `cache.delete(ALIAS_CACHE_KEY)`

**State Management (Vue):**
- No Vuex/Pinia; state lives in component `data` / `ref` / `reactive`
- `MealPlanApp.vue` (list) fetches all plans on mount, filters client-side
- `MealPlanDetailApp.vue` (detail) fetches plan data on mount, patches via `PUT`/`PATCH` on user actions
- URL state synced via `history.pushState` (search query, page number)

## Key Abstractions

**`NUTRIENTS` ordered dict:**
- Purpose: Single source of truth mapping nutrient keys → label, unit, Food model field, display precision
- Location: `meals/nutrients.py`
- Pattern: Imported by models (`NUTRIENT_IDS`, `THRESHOLD_SCHEMA`), views (`get_meal_plan_context`, `meal_plan_detail`), serializers (indirectly via model)

**`get_alias_index()`:**
- Purpose: Cache-backed dict (`food_id → [alias_string]`) for O(n) alias lookups without per-request DB queries
- Location: `meals/models.py`
- Pattern: Call `get_alias_index()` in hot paths; never call `FoodAlias.objects.filter(...)` directly in search

**`get_meal_plan_context(pk)`:**
- Purpose: Shared context builder for both PDF generation and preview rendering
- Location: `meals/views.py`
- Pattern: Returns dict with `plan`, `days_data`, `summary_nutrients`, `visible_nutrients`, `all_nutrients`; consumed by `meal_plan_pdf` and `meal_plan_preview_content`

**`SiteSettings.get()`:**
- Purpose: Singleton accessor for site-wide configuration (logo files)
- Location: `meals/models.py`
- Pattern: Always use `SiteSettings.get()` — never `SiteSettings.objects.get(pk=1)`

**MealPlan validation chain:**
- Purpose: Guarantee JSON field integrity on every save
- Pattern: `MealPlan.save()` → `full_clean()` → `clean()` (migrates old nutrient keys + validates `thresholds` via `THRESHOLD_SCHEMA`); `MealPlanSerializer.validate()` catches `ValidationError` and re-raises as DRF error

## Entry Points

**WSGI/ASGI:**
- Location: `config/wsgi.py`, `config/asgi.py`
- Triggers: gunicorn (production), `uv run python manage.py runserver` (dev)
- Responsibilities: Bootstrap Django application object

**Root URL conf:**
- Location: `config/urls.py`
- Responsibilities: Mount admin, i18n, media serving, delegate all app paths to `meals.urls`

**Vue SPAs (four independent entry points):**
- `frontend/src/mealplan-list/main.js` — mounts `MealPlanApp` on `#meal-plan-app`
- `frontend/src/mealplan-detail/main.js` — mounts `MealPlanDetailApp` on its mount element
- `frontend/src/food-database/main.js` — mounts `FoodDatabaseApp`
- `frontend/src/food-editor/main.js` — mounts `FoodEditorApp`

**Management Commands:**
- `meals/management/commands/import_foods.py` — BLS Excel importer; called once per data refresh
- `meals/management/commands/build_scss.py` — compiles SCSS to `sass_cache/`; called in CI and Dockerfile before `collectstatic`

## Error Handling

**Strategy:** Validation at model layer; DRF serializers catch and re-raise; HTTP status codes for API clients; template views use `get_object_or_404`

**Patterns:**
- `MealPlan.save()` always calls `full_clean()`; invalid data raises `ValidationError` before DB write
- `MealPlanSerializer.validate()` wraps `full_clean()` to convert `django.core.exceptions.ValidationError` → `rest_framework.exceptions.ValidationError` (prevents 500s)
- `FoodSerializer.validate()` raises 400 if both energy fields are supplied simultaneously; computes the missing field otherwise
- `FoodViewSet.update()` / `destroy()` return 403 for non-custom foods
- Template views use `get_object_or_404` for all PK lookups

## Cross-Cutting Concerns

**Logging:** `logging.StreamHandler` to stdout; level `INFO` by default (configurable via `DJANGO_LOG_LEVEL` env var); no structured logging library

**Validation:** Model-level via `MealPlan.full_clean()`; serializer-level via DRF `validate()` methods; JSON field schema validated with `jsonschema` against `THRESHOLD_SCHEMA`

**Authentication:** Django session authentication for template views (`@login_required`); DRF `IsAuthenticated` permission class for all API endpoints; login/logout via Django's built-in `auth` views

**i18n:** `LocaleMiddleware` active; `USE_I18N = True`; `LANGUAGE_CODE = 'en'`; translation strings use `gettext_lazy` (models, nutrients) and `gettext` (views, default names); `.po` files in `meals/locale/de/` and `meals/locale/en/`; Vue SPA i18n strings are rendered server-side and injected via `data-i18n` attribute

**Static files:** SCSS compiled by `django-sass-processor` (dev on-demand via `{% sass_src %}`) or `build_scss` command (CI/prod); Vue bundles built by Vite via `pnpm build`; served by WhiteNoise middleware in production

---

*Architecture analysis: 2026-03-16*
