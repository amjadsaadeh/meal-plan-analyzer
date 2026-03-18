# Codebase Concerns

**Analysis Date:** 2026-03-16

## Tech Debt

**No multi-tenancy / data isolation:**
- Issue: All authenticated users see and can mutate all `MealPlan`, `MealPlanDay`, `MealPlanFood`, `ThresholdPreset`, and `FoodAlias` records — no ownership column or per-user queryset filtering exists anywhere.
- Files: `meals/views.py` (all ViewSet `get_queryset` methods), `meals/models.py`
- Impact: Any logged-in user can read, edit, or delete another user's meal plans via the API. This is a correctness issue if the app ever has more than one real user.
- Fix approach: Add a `owner = ForeignKey(User)` to `MealPlan` and `ThresholdPreset`, filter all ViewSet querysets to `request.user`, migrate existing rows.

**`data_source` field has two distinct values meaning "BLS-imported":**
- Issue: Foods imported via `import_foods` are stored with `data_source='bls'`, but the CLAUDE.md documentation states "BLS-imported foods have `data_source=''`". The `Food` model default is `""` (blank). Tests create BLS-like foods without setting `data_source`, so the fixture foods have `data_source=""`. Real-imported foods get `data_source="bls"`. The edit/delete guards in `FoodViewSet` only check `!= 'custom'`, so they work regardless, but the inconsistency is misleading.
- Files: `meals/management/commands/import_foods.py` line 242, `meals/models.py` line 59, `CLAUDE.md`
- Impact: Documentation is wrong; future code or tests that check `data_source == ""` for BLS foods will be wrong for re-imported data. No test asserts the imported value of `data_source`.
- Fix approach: Settle on one value (`""` or `"bls"`), update import command and documentation consistently. Add an assertion in `test_food_import.py`.

**`playwright` pinned in production dependencies (not dev):**
- Issue: `playwright==1.56.0` is listed in `[project].dependencies` (production), not `[dependency-groups].dev`. This means the full Playwright browser runtime ships in the production Docker image.
- Files: `pyproject.toml` line 30
- Impact: Bloated production image (~200 MB+ extra). No security benefit from this package in prod.
- Fix approach: Move `playwright==1.56.0` to `[dependency-groups].dev` alongside `pytest-playwright`.

**Inline / deferred imports scattered through `views.py`:**
- Issue: Several stdlib and Django imports are placed in the middle of the file or inside function bodies (e.g., `from django.shortcuts import redirect` inside `meal_plan_detail`, `import json` at line 171, `from django.db.models import Prefetch` at line 500, `from django.http import HttpResponse` at line 572, `from urllib.parse import urlparse` at line 750).
- Files: `meals/views.py` lines 110–114, 167, 171, 500, 538, 572, 725, 744, 750
- Impact: Reduces readability, can hide circular import issues, complicates static analysis.
- Fix approach: Move all imports to the top of `views.py`.

**`ThresholdPreset` model is a flat column-per-nutrient explosion:**
- Issue: `ThresholdPreset` has 52 explicit `FloatField` columns (one `_min`/`_max` pair per nutrient). Adding a new nutrient requires adding 2 fields to this model and creating a migration.
- Files: `meals/models.py` lines 68–148
- Impact: Schema churn with every nutrient addition; high duplication. The `MealPlan.thresholds` JSON field solves the same problem more flexibly.
- Fix approach: Long-term, replace `ThresholdPreset` flat fields with a single JSON field matching the `MealPlan.thresholds` schema; keep the existing columns until a migration path exists.

**`get_meal_plan_context` is not protected by `@login_required`:**
- Issue: `get_meal_plan_context(pk)` is a plain function callable from PDF and preview views. If it is ever called from a path that is not behind `@login_required`, unauthenticated users could access any meal plan's data.
- Files: `meals/views.py` lines 577–722
- Impact: Low risk currently (all callers do require login), but fragile — a new caller could accidentally bypass auth.
- Fix approach: Pass `request` into the function and verify authentication, or make it a method on the view class.

**`csrf_token_string` placeholder in context:**
- Issue: The `get_meal_plan_context` return dict has `"csrf_token_string": ""` with a comment "We'll handle CSRF from the request if needed". The value is never populated.
- Files: `meals/views.py` line 721
- Impact: If any template ever uses `{{ csrf_token_string }}` expecting a real token, it will silently produce an empty string, breaking CSRF protection.
- Fix approach: Either populate it from `request` (`from django.middleware.csrf import get_token; get_token(request)`) or remove the key entirely if unused.

## Known Bugs

**Food search with a search term bypasses pagination and returns all results:**
- Symptoms: `GET /api/foods/?search=a` returns every matching food in a single unbounded list (no `count`/`next`/`previous` envelope).
- Files: `meals/views.py` lines 392–438 (`FoodViewSet.list`)
- Trigger: Any request with a non-empty `?search=` parameter to `/api/foods/`.
- Workaround: This is intentional for the food-search dropdown use case, but it means a broad query like `?search=e` can return thousands of rows.

**`MealPlanDay.meal_plan` is nullable but the app never explicitly handles orphaned days:**
- Symptoms: `meal_plan = ForeignKey(MealPlan, null=True, blank=True)` can produce `MealPlanDay` rows with no parent plan. There is no cleanup or guard.
- Files: `meals/models.py` lines 229–230
- Trigger: Possible if a plan is deleted without CASCADE (CASCADE is set, so this is low risk) or if a day is created programmatically without a plan.
- Workaround: CASCADE delete on plan covers most cases; orphaned rows are hidden by the `removed=False` filter.

## Security Considerations

**No per-object ownership enforcement:**
- Risk: Any authenticated user can `GET /api/mealplans/`, `PATCH /api/mealplan-foods/<id>/`, `DELETE /api/mealplans/<id>/` on records belonging to other users.
- Files: `meals/views.py` — all ViewSet classes
- Current mitigation: `IsAuthenticated` at the DRF global level; must be logged in.
- Recommendations: Add per-object permission checks (e.g., a custom `IsOwner` permission class) and user FK on ownable models.

**`docker-compose.yml` uses `DEBUG=True` and a hardcoded weak `SECRET_KEY` fallback:**
- Risk: The Compose file sets `DEBUG=True` and `SECRET_KEY=${SECRET_KEY:-change-me-generate-a-real-key-for-production}`. If accidentally used in production without overriding `SECRET_KEY`, Django's debug mode and the weak key are live.
- Files: `docker-compose.yml`
- Current mitigation: This is documented as a local dev compose file.
- Recommendations: Change the fallback to a value that explicitly fails startup (e.g., empty string that raises `ImproperlyConfigured`), or add a settings guard that raises if `SECRET_KEY` equals the placeholder.

**`SECURE_PROXY_SSL_HEADER` and `USE_X_FORWARDED_*` are always on:**
- Risk: `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` is unconditionally set. If the app is accessed without a trusted reverse proxy (e.g., direct gunicorn on dev), a client can spoof HTTPS by sending `X-Forwarded-Proto: https`.
- Files: `config/settings.py` lines 49–51
- Current mitigation: `DEBUG=True` for local dev; gunicorn only binds to internal addresses in Docker.
- Recommendations: Gate these settings on `not DEBUG` or on an explicit `BEHIND_PROXY` env var.

**File uploads stored without content-type validation:**
- Risk: `SiteSettings.logo` and `SiteSettings.minilogo` accept any file (`FileField`). A malicious admin could upload a non-image file; WeasyPrint would attempt to process it.
- Files: `meals/models.py` lines 267–272
- Current mitigation: Admin access is required to upload; `FileField` does not validate type.
- Recommendations: Use `ImageField` instead of `FileField` to enforce image-type validation at the Django level.

## Performance Bottlenecks

**`import_foods` performs one `update_or_create` per row (no bulk operations):**
- Problem: Importing the full BLS dataset (~18,000 food items) issues 18,000 individual SQL `UPDATE`/`INSERT` statements.
- Files: `meals/management/commands/import_foods.py` lines 212–244
- Cause: `Food.objects.update_or_create(...)` called inside a Python loop with no batching or transaction boundary.
- Improvement path: Wrap the loop in `with transaction.atomic():`, and consider `bulk_create` with `update_conflicts=True` (Django 4.2+) for a significant speedup.

**Food search with umlaut expansion can issue many `LIKE` queries per search request:**
- Problem: `get_food_search_query` generates up to `2^n − 1` umlaut variants for the entire query plus each split term, all ORed as `icontains` (`LIKE '%...%'`) clauses. For a 6-position word, this is up to 63 extra DB `LIKE` predicates per search request.
- Files: `meals/views.py` lines 275–291 (`get_food_search_query`), lines 46–107 (`_umlaut_search_variants`)
- Cause: No full-text search index; substring `LIKE` queries on `name` and `bls_code` without a DB index.
- Improvement path: Add a `db_index=True` on `Food.name`, or adopt PostgreSQL full-text search / trigram indexes (`pg_trgm`) for the production DB.

**No database index on `Food.name` or `Food.bls_code`:**
- Problem: All food search queries use `name__icontains` and `bls_code__icontains`. With thousands of rows and no index, each search performs a full table scan.
- Files: `meals/models.py` lines 31–32
- Cause: Neither field has `db_index=True`.
- Improvement path: Add `db_index=True` to `Food.name` and `Food.bls_code`. For PostgreSQL, a `gin` or `gist` trigram index would also help `LIKE` queries.

**PDF generation blocks the request thread:**
- Problem: `meal_plan_pdf` calls `weasyprint.HTML(...).write_pdf()` synchronously in the web worker. WeasyPrint can take several seconds for complex plans.
- Files: `meals/views.py` lines 790–824
- Cause: No async task queue; PDF is generated inline.
- Improvement path: Move PDF generation to a background task (Celery, Django-Q) and return a download link, or accept the limitation for small single-user deployments.

## Fragile Areas

**Cache backend defaults to Django's in-memory `LocMemCache`:**
- Files: `config/settings.py` (no `CACHES` setting configured)
- Why fragile: Django's default cache backend is `LocMemCache`, which is process-local and not shared between gunicorn workers. In a multi-worker deployment, the alias cache (`food_aliases_index`) is not invalidated across workers — one worker may serve stale aliases while another has the fresh cache.
- Safe modification: Add a `CACHES` setting pointing to a shared backend (Redis, Memcached) for production. Document this in `.env.example`.
- Test coverage: Tests clear the cache manually with `cache.delete(ALIAS_CACHE_KEY)` in `setup_method` and are not affected.

**`MealPlan.save()` always calls `full_clean()` — breaks raw `update()` calls:**
- Files: `meals/models.py` lines 222–224
- Why fragile: Any future code using `MealPlan.objects.filter(...).update(...)` bypasses `full_clean()` and can write invalid `thresholds` / `visible_nutrients` JSON to the database silently.
- Safe modification: Always use `.save()` for `MealPlan` instances. Never use `QuerySet.update()` on this model. Document this constraint clearly.
- Test coverage: `tests/test_model_validation.py` tests `save()` path; `update()` bypass is untested.

**`MealPlanSerializer.validate` instantiates a throwaway `MealPlan(**attrs)` for validation:**
- Files: `meals/serializers.py` lines 145–158
- Why fragile: A transient `MealPlan()` instance is created with `**attrs` and `full_clean()` called on it. This will not work correctly for partial updates (`PATCH`) where only some fields are provided, because the instance defaults may not match the existing database row.
- Safe modification: For PATCH, fetch the existing instance and apply `attrs` before calling `full_clean()`.
- Test coverage: Partial update edge cases (e.g., patching only `name` without `thresholds`) may silently skip validation.

**Hard-coded BLS column indices in `import_foods`:**
- Files: `meals/management/commands/import_foods.py` lines 138–165
- Why fragile: Column letters are hard-coded constants (e.g., `IDX_OMEGA3 = col_to_idx("LA")`). If the BLS Excel schema changes in a future release, the import will silently read wrong columns or crash.
- Safe modification: Add a header-row validation step that confirms expected column headers before importing.
- Test coverage: `tests/test_food_import.py` uses a controlled fixture xlsx; BLS column layout changes are not tested.

## Scaling Limits

**In-memory alias index:**
- Current capacity: All `FoodAlias` rows are loaded into a Python dict in memory per worker process.
- Limit: At very high alias counts (tens of thousands), the in-memory dict may become large, and cache misses (after invalidation) cause a full `SELECT` rebuild.
- Scaling path: Use a Redis hash or maintain a database-level index with trigram search.

**`MealPlanViewSet` fetches all plans for all users:**
- Current capacity: Works for small user bases.
- Limit: With many users and plans, `MealPlan.objects.all()` grows unbounded. Currently paginated at 100/page in the Vue list (client-side pagination over the full API response).
- Scaling path: Add user ownership and filter querysets per user; server-side pagination is already in the Vue list component.

## Dependencies at Risk

**`playwright==1.56.0` pinned exactly in production deps:**
- Risk: Pinned to a specific minor version in production dependencies; browser binaries must match the pinned version exactly. Falling out of date with upstream security fixes.
- Impact: Test suite may fail if Playwright browsers are not installed, or if CI installs a different version via `pytest-playwright`.
- Migration plan: Move to dev dependencies; use `>=` constraint and reconcile with `pytest-playwright` version.

**`weasyprint>=68.0` requires system-level native libraries:**
- Risk: WeasyPrint depends on libpango, libcairo, libharfbuzz and related packages. These must be installed on every deployment target manually. Missing libraries cause silent runtime failures (PDF generation returns empty or crashes).
- Impact: Not installable in minimal environments without the apt package list from the Dockerfile.
- Migration plan: Consider `reportlab` or `fpdf2` as pure-Python alternatives, or document system requirements more prominently.

## Missing Critical Features

**No rate limiting on search or authentication endpoints:**
- Problem: `/api/foods/?search=` and `/login/` have no rate limiting. The food search path with umlaut expansion can be computationally expensive.
- Blocks: Resistance to brute-force login and search-based DoS.

**No user-scoped data isolation:**
- Problem: No model has an `owner` / `created_by` field linked to `django.contrib.auth.models.User`.
- Blocks: Multi-user deployments where users should not see each other's meal plans.

## Test Coverage Gaps

**`data_source` value after BLS import is not asserted:**
- What's not tested: `test_food_import.py` does not assert `food.data_source == "bls"` after import; the documentation says it should be `""`.
- Files: `tests/test_food_import.py`
- Risk: The inconsistency between docs and code could go unnoticed.
- Priority: Low

**Multi-worker cache invalidation is not tested:**
- What's not tested: The alias cache being stale across separate gunicorn workers (LocMemCache issue).
- Files: `tests/api/test_foods.py`
- Risk: In production with multiple workers, stale aliases could be served indefinitely until the worker restarts.
- Priority: Medium

**`MealPlanSerializer` PATCH with missing required fields:**
- What's not tested: Calling `PATCH /api/mealplans/<id>/` with only a `name` field; the transient instance instantiation in `validate` may skip threshold validation.
- Files: `tests/api/test_mealplans.py`, `meals/serializers.py`
- Risk: Invalid thresholds can silently bypass validation on partial update.
- Priority: Medium

**Authorization: cross-user data access:**
- What's not tested: No test verifies that User A cannot read or modify User B's meal plans via the API.
- Files: `tests/api/` (all test files lack a second user fixture)
- Risk: If multi-tenancy is ever intended, this gap means authorization bugs would ship undetected.
- Priority: High (if multi-user support is a goal)

**PDF generation under error conditions:**
- What's not tested: What happens if WeasyPrint raises an exception (e.g., missing system library in a stripped environment). The view has no error handling around `html.write_pdf()`.
- Files: `meals/views.py` lines 815–816, `tests/test_pdf_views.py`
- Risk: Unhandled exception returns a 500 to the user with no meaningful message.
- Priority: Low

---

*Concerns audit: 2026-03-16*
