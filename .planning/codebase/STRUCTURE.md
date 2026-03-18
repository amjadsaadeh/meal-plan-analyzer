# Codebase Structure

**Analysis Date:** 2026-03-16

## Directory Layout

```
meal-plan-analyzer/
├── config/                        # Django project configuration
│   ├── settings.py                # All settings via django-environ
│   ├── urls.py                    # Root URL conf (admin, i18n, delegates to meals.urls)
│   ├── wsgi.py                    # WSGI entry point
│   └── asgi.py                    # ASGI entry point
│
├── meals/                         # The sole Django app — all domain logic lives here
│   ├── models.py                  # All data models + cache helpers + signals
│   ├── views.py                   # Template views + DRF ViewSets + search helpers
│   ├── serializers.py             # DRF serializers for all models
│   ├── urls.py                    # App URL patterns + DRF DefaultRouter at /api/
│   ├── nutrients.py               # NUTRIENTS dict, NUTRIENT_IDS list, THRESHOLD_SCHEMA
│   ├── admin.py                   # Django admin registrations
│   ├── apps.py                    # App config (name: meals)
│   ├── context_processors.py      # app_version context processor
│   ├── templatetags/
│   │   └── meal_extras.py         # Custom filters: divide_by_100_mult, split_to_dict, get_item, get_attr
│   ├── templates/meals/           # All Django templates (extension: .html.j2)
│   │   ├── base.html.j2           # Base layout (extends nothing)
│   │   ├── login.html.j2
│   │   ├── mealplan_list.html.j2  # Mounts #meal-plan-app Vue SPA
│   │   ├── mealplan_detail.html.j2  # Mounts mealplan-detail Vue SPA
│   │   ├── mealplan_pdf.html.j2   # PDF content (shared with preview)
│   │   ├── mealplan_preview.html.j2 # Preview iframe wrapper
│   │   ├── index.html.j2          # Food search page shell
│   │   ├── food_database.html.j2  # Mounts food-database Vue SPA
│   │   └── food_editor.html.j2    # Mounts food-editor Vue SPA
│   ├── static/meals/
│   │   ├── img/                   # Static images (logo.png, etc.)
│   │   └── scss/                  # SCSS source files
│   │       ├── main.scss          # Main entry point
│   │       ├── mealplan_detail.scss
│   │       ├── mealplan_list.scss
│   │       ├── mealplan_preview.scss
│   │       ├── pdf.scss
│   │       ├── food_search.scss
│   │       ├── food_database.scss
│   │       ├── food_editor.scss
│   │       ├── login.scss
│   │       ├── _layout.scss       # Shared layout partial
│   │       ├── _reset.scss        # CSS reset partial
│   │       └── _variables.scss    # SCSS variables partial
│   ├── migrations/                # Django migrations (0001–0024)
│   ├── locale/
│   │   ├── de/LC_MESSAGES/django.po   # German translations
│   │   └── en/LC_MESSAGES/django.po   # English translations
│   └── management/commands/
│       ├── import_foods.py        # BLS Excel importer
│       └── build_scss.py          # SCSS compilation command
│
├── frontend/                      # Vue 3 / Vite front-end source
│   ├── src/
│   │   ├── mealplan-list/         # Meal plan list SPA
│   │   │   ├── main.js            # Vite entry point
│   │   │   └── components/        # MealPlanApp.vue, SearchBar.vue, MealPlanTable.vue,
│   │   │                          #   MealPlanRow.vue, DayBadge.vue, Pagination.vue,
│   │   │                          #   ConfirmDeleteModal.vue
│   │   ├── mealplan-detail/       # Meal plan detail SPA
│   │   │   ├── main.js            # Vite entry point
│   │   │   └── components/        # MealPlanDetailApp.vue, DaySection.vue, MealSection.vue,
│   │   │                          #   IngredientRow.vue, FoodSearchDropdown.vue, Toolbar.vue,
│   │   │                          #   PlanOverview.vue, DaySidePanel.vue, StickyBar.vue,
│   │   │                          #   PageHeader.vue, SavePresetModal.vue,
│   │   │                          #   ConfirmDeleteDayModal.vue, ConfirmDeleteIngredientModal.vue
│   │   ├── food-database/         # Food database browser SPA
│   │   │   ├── main.js            # Vite entry point
│   │   │   └── components/        # FoodDatabaseApp.vue, FoodTable.vue, FoodRow.vue,
│   │   │                          #   FoodSearchBar.vue, Pagination.vue
│   │   └── food-editor/           # Food editor SPA
│   │       ├── main.js            # Vite entry point
│   │       └── components/        # FoodEditorApp.vue
│   └── dist/                      # Vite build output (gitignored; in STATICFILES_DIRS)
│       └── .vite/manifest.json    # Asset manifest read by django-vite
│
├── tests/                         # Full test suite
│   ├── conftest.py                # Shared fixtures: api_client, user, authenticated_client
│   ├── data/
│   │   ├── food_fixtures.json     # Session-scoped seed data loaded by conftest
│   │   ├── test_foods.xlsx        # Excel file for import tests
│   │   ├── test_foods_Daten.zip   # ZIP with BLS Daten file for import tests
│   │   └── test_foods_no_daten.zip  # ZIP without Daten (import error tests)
│   ├── api/                       # DRF endpoint tests (pytest.mark.django_db)
│   │   ├── test_foods.py
│   │   ├── test_mealplans.py
│   │   ├── test_mealplandays.py
│   │   ├── test_mealplan_foods.py
│   │   ├── test_threshold_presets.py
│   │   ├── test_food_search_semantics.py
│   │   ├── test_export_name_auto_alias.py
│   │   └── test_food_energy_sync.py
│   ├── frontend/                  # Playwright browser tests
│   │   ├── conftest.py            # logged_in_page fixture
│   │   ├── factories.py           # factory-boy: FoodFactory, MealPlanFactory,
│   │   │                          #   MealPlanDayFactory, MealPlanFoodFactory
│   │   ├── test_mealplan_list.py
│   │   ├── test_mealplan_detail.py
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
├── deployment/                    # Infrastructure as code
│   ├── app-deployment/
│   │   ├── ansible/               # Ansible playbooks for k3s deployment
│   │   └── k8s/                   # Kustomize manifests (base + dev/prod overlays)
│   └── bootstrap/
│       ├── ansible/               # Bootstrap playbooks
│       └── k8s/                   # Bootstrap k8s manifests
│
├── docs/plans/                    # Development plans and documentation
│
├── sass_cache/                    # Compiled CSS output (gitignored; in STATICFILES_DIRS)
├── staticfiles/                   # collectstatic output (gitignored)
├── media/                         # User-uploaded files (logos)
│
├── .agent/                        # AI agent rules and workflows
│   ├── rules/                     # backend-package-manager.md, running-backend-tests.md
│   └── workflows/                 # run-tests.md
│
├── .planning/codebase/            # Codebase analysis documents (this file's location)
│
├── vite.config.js                 # Vite build config (4 entry points → frontend/dist/)
├── pyproject.toml                 # Python project metadata + all dependencies
├── uv.lock                        # uv lockfile (must stay in sync with pyproject.toml)
├── package.json                   # JS project metadata
├── pnpm-lock.yaml                 # pnpm lockfile
├── pytest.ini                     # Test runner config (DJANGO_SETTINGS_MODULE, --reuse-db)
├── Dockerfile                     # Multi-stage build (node-builder + uv-builder + final)
├── docker-compose.yml             # Local dev with PostgreSQL
└── .env.example                   # Environment variable template
```

## Directory Purposes

**`config/`:**
- Purpose: Django project-level configuration (not app code)
- Key files: `settings.py` (all settings, reads `.env`), `urls.py` (root routing)

**`meals/`:**
- Purpose: The entire application domain — models, API, views, templates, static assets, i18n, management commands
- Key files: `models.py`, `views.py`, `serializers.py`, `urls.py`, `nutrients.py`
- Note: This is a single-app Django project; all business logic lives here

**`meals/templates/meals/`:**
- Purpose: HTML templates; use `.html.j2` extension (processed by Django template engine, not Jinja2)
- Pattern: Pages with Vue SPAs are thin shells that mount `#<name>-app` div elements

**`meals/static/meals/scss/`:**
- Purpose: SCSS source — entry points (no prefix) are compiled; partials (prefixed `_`) are imported
- Note: Do NOT edit `sass_cache/` directly; edit source here

**`frontend/src/`:**
- Purpose: Vue 3 SPA source, split into four independent apps matching the four interactive pages
- Each subdirectory is a separate Vite entry point; components live in `components/` subdirectory

**`frontend/dist/`:**
- Purpose: Vite build output; added to `STATICFILES_DIRS` so Django serves the JS/CSS assets
- Generated: Yes; never edit manually; committed: No (gitignored)

**`tests/`:**
- Purpose: All test code — API tests, Playwright frontend tests, unit/integration tests
- Key file: `tests/conftest.py` (shared fixtures); `tests/frontend/factories.py` (factory-boy factories)
- Test data: `tests/data/food_fixtures.json` auto-loaded once per session

**`deployment/`:**
- Purpose: Kubernetes manifests and Ansible playbooks for production deployment to k3s
- Not used for local development

## Key File Locations

**Entry Points:**
- `config/wsgi.py`: WSGI application object
- `config/asgi.py`: ASGI application object
- `manage.py`: Django management CLI

**Configuration:**
- `config/settings.py`: All Django settings (environment-driven)
- `.env.example`: Template for required environment variables
- `pytest.ini`: Test runner settings (`DJANGO_SETTINGS_MODULE`, `--reuse-db`)
- `vite.config.js`: Vite build configuration

**Core Logic:**
- `meals/models.py`: All data models, signals, `get_alias_index()`, `ALIAS_CACHE_KEY`
- `meals/nutrients.py`: `NUTRIENTS` dict, `NUTRIENT_IDS`, `THRESHOLD_SCHEMA`
- `meals/views.py`: All views and ViewSets, food search helpers, `get_meal_plan_context()`
- `meals/serializers.py`: All DRF serializers with cross-field validation

**Routing:**
- `config/urls.py`: Root URL conf
- `meals/urls.py`: App URL conf + DRF router

**Testing:**
- `tests/conftest.py`: `api_client`, `user`, `authenticated_client` fixtures
- `tests/frontend/conftest.py`: `logged_in_page` Playwright fixture
- `tests/frontend/factories.py`: factory-boy model factories

**Static Assets:**
- `meals/static/meals/scss/main.scss`: Primary SCSS entry point
- `frontend/src/mealplan-detail/main.js`: Most complex Vue SPA entry point

## Naming Conventions

**Python files:**
- `snake_case.py` throughout
- Template tags module: `meal_extras.py`
- Management commands: descriptive snake_case (`import_foods.py`, `build_scss.py`)

**Templates:**
- `<page_name>.html.j2` — lowercase with underscores, `.html.j2` extension always
- Partials: none (no Django template partials; full inheritance via `base.html.j2`)

**SCSS files:**
- Entry points: `<page_name>.scss` (e.g. `mealplan_detail.scss`)
- Partials: `_<name>.scss` (e.g. `_variables.scss`, `_layout.scss`)

**Vue files:**
- Components: `PascalCase.vue` (e.g. `MealPlanApp.vue`, `FoodSearchBar.vue`)
- Entry points: `main.js`
- SPA directories: `kebab-case` matching the page (e.g. `mealplan-list/`, `food-editor/`)

**URL names:**
- Kebab-case strings (e.g. `meal-plan-detail`, `food-database`, `meal-plan-pdf`)

**Model fields:**
- `<nutrient>_per_100g` suffix on `Food` model fields (e.g. `protein_in_g_per_100g`)
- `<nutrient>_min` / `<nutrient>_max` on `ThresholdPreset`
- Nutrient keys in `NUTRIENTS` dict omit the `_per_100g` suffix (e.g. `protein_in_g`)

## Where to Add New Code

**New nutrient:**
1. Add `FloatField` to `Food` in `meals/models.py`
2. Add entry to `NUTRIENTS` dict in `meals/nutrients.py`
3. Add `_min` / `_max` `FloatField` pair to `ThresholdPreset` in `meals/models.py`
4. Create a new migration: `uv run python manage.py makemigrations`
5. Update `FoodSerializer` fields list in `meals/serializers.py`

**New API endpoint:**
1. Add ViewSet in `meals/views.py`
2. Add serializer in `meals/serializers.py`
3. Register with `router` in `meals/urls.py`

**New template view (server-rendered page):**
1. Add view function in `meals/views.py` with `@login_required`
2. Add template at `meals/templates/meals/<page_name>.html.j2`
3. Add SCSS entry point at `meals/static/meals/scss/<page_name>.scss`
4. Add URL pattern in `meals/urls.py`

**New Vue SPA page:**
1. Create `frontend/src/<page-name>/main.js` and `frontend/src/<page-name>/components/`
2. Add entry to `rollupOptions.input` in `vite.config.js`
3. Create Django template shell that mounts the SPA div
4. Follow existing pattern: pass i18n strings and API URLs via `data-*` attributes

**New test:**
- API tests: `tests/api/test_<feature>.py` with `@pytest.mark.django_db`
- Frontend tests: `tests/frontend/test_<feature>.py` using `logged_in_page` fixture
- Unit/model tests: `tests/test_<feature>.py`
- Test factories: add to `tests/frontend/factories.py`

**Shared utilities:**
- Python helpers used by views: add to `meals/views.py` as module-level functions (small helpers) or consider a new `meals/utils.py` for larger additions
- Template filters: add to `meals/templatetags/meal_extras.py`

## Special Directories

**`sass_cache/`:**
- Purpose: Compiled CSS output from `django-sass-processor` and `build_scss` command
- Generated: Yes (by `{% sass_src %}` tag in dev, `build_scss` in CI/prod)
- Committed: No (gitignored)
- Listed in `STATICFILES_DIRS` so `collectstatic` picks up the CSS

**`frontend/dist/`:**
- Purpose: Vite bundle output (JS, CSS, assets + `.vite/manifest.json`)
- Generated: Yes (by `pnpm build`)
- Committed: No (gitignored)
- Listed in `STATICFILES_DIRS`; `django-vite` reads `manifest.json` for asset URLs

**`staticfiles/`:**
- Purpose: `collectstatic` output for production serving
- Generated: Yes (by `python manage.py collectstatic`)
- Committed: No
- Served by WhiteNoise middleware in production

**`media/`:**
- Purpose: User-uploaded files (site logo, mini-logo via `SiteSettings`)
- Generated: Yes (at runtime)
- Committed: No

**`.planning/codebase/`:**
- Purpose: Codebase analysis documents for AI-assisted development
- Generated: Yes (by GSD mapping agent)
- Committed: Yes

---

*Structure analysis: 2026-03-16*
