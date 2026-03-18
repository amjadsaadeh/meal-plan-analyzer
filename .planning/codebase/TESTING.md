# Testing Patterns

**Analysis Date:** 2026-03-16

## Test Framework

**Runner:**
- `pytest` 9.x with `pytest-django` 4.x
- Config: `pytest.ini` (project root)
- Settings: `DJANGO_SETTINGS_MODULE = config.settings`
- Default flag: `--reuse-db` (test database is reused between runs)

**Assertion Library:**
- pytest's built-in `assert` — no separate library
- `pytest.approx` for float comparisons: `assert divide_by_100_mult(10, 100) == pytest.approx(10.0)`
- `pytest.raises` for exception assertions

**Browser Testing:**
- `pytest-playwright` 0.7.x with Chromium
- `playwright.sync_api.expect` for assertions on page state

**Run Commands:**
```bash
uv run pytest                               # full suite
uv run pytest tests/api/                    # API tests only
uv run pytest tests/frontend/               # Playwright browser tests only
uv run pytest tests/test_*.py               # unit/integration tests only
uv run pytest --create-db                   # force test DB rebuild (after migrations)
uv run pytest -v --tb=short                 # verbose with short tracebacks
```

## Test File Organization

**Location:**
- All tests in `tests/` directory (separate from source)
- Three sub-areas: `tests/api/`, `tests/frontend/`, `tests/test_*.py` (top-level)

**Naming:**
- Files: `test_<subject>.py` — `test_foods.py`, `test_model_validation.py`, `test_search_utilities.py`
- Classes: `Test<Subject>` — `TestFoodAPI`, `TestMealPlanAPI`, `TestFoodAliasSearch`
- Functions: `test_<what_is_expected>` — `test_list_foods_unauthenticated`, `test_alias_index_populated_after_creation`

**Structure:**
```
tests/
├── conftest.py                  # shared fixtures: api_client, user, authenticated_client
├── data/
│   ├── food_fixtures.json       # session-scoped seed data (100 foods)
│   ├── test_foods.xlsx          # for food import tests
│   └── test_foods_Daten.zip
├── api/
│   ├── test_foods.py
│   ├── test_mealplans.py
│   ├── test_mealplandays.py
│   ├── test_mealplan_foods.py
│   ├── test_threshold_presets.py
│   ├── test_food_search_semantics.py
│   ├── test_export_name_auto_alias.py
│   └── test_food_energy_sync.py
├── frontend/
│   ├── conftest.py              # Playwright fixtures: logged_in_page, meal_plan_with_day
│   ├── factories.py             # factory-boy factories
│   ├── test_mealplan_list.py
│   ├── test_mealplan_detail.py
│   └── test_pdf.py
├── test_admin.py
├── test_error_handling.py
├── test_extended_backend.py
├── test_food_import.py
├── test_meal_plan_context.py
├── test_model_constraints.py
├── test_model_validation.py
├── test_nutrients.py
├── test_pdf_views.py
├── test_search_utilities.py
└── test_template_filters.py
```

## Test Structure

**Suite Organization:**

API and unit tests use `@pytest.mark.django_db` on a class, with each method being one focused test:

```python
@pytest.mark.django_db
class TestFoodAPI:
    def test_list_foods_unauthenticated(self, api_client):
        """Test getting all foods without authentication."""
        response = api_client.get("/api/foods/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_foods_authenticated(self, authenticated_client):
        """Test getting all foods with authentication (paginated)."""
        response = authenticated_client.get("/api/foods/")
        assert response.status_code == status.HTTP_200_OK
```

Unit tests for pure logic (no DB) skip the mark entirely:

```python
class TestDivideBy100Mult:
    def test_basic_calculation(self):
        assert divide_by_100_mult(10, 100) == pytest.approx(10.0)
```

Frontend tests use module-level `pytestmark`:

```python
pytestmark = pytest.mark.django_db

def test_mealplan_list_basic(logged_in_page, live_server, test_user):
    MealPlanFactory.create_batch(3)
    logged_in_page.goto(live_server.url + "/")
    expect(logged_in_page.locator(".meal-plan-row")).to_have_count(3)
```

**Docstrings on test methods:**
Single-line docstrings describe the expected behaviour: `"""Test getting all foods without authentication."""`

**Section dividers:**
Long test files use `# ---` separator blocks to group related tests:
```python
# ---------------------------------------------------------------------------
# Alias search tests
# ---------------------------------------------------------------------------
```

## Mocking

**Framework:** No mocking library used — tests use real database objects.

**Cache management (instead of mocking):**
- Tests that touch `FoodAlias` manually invalidate the Django cache using `cache.delete(ALIAS_CACHE_KEY)` in `setup_method` / `teardown_method` or in autouse fixtures:
```python
def setup_method(self):
    cache.delete(ALIAS_CACHE_KEY)

def teardown_method(self):
    cache.delete(ALIAS_CACHE_KEY)
```

- With `autouse=True` fixture and `yield`:
```python
@pytest.fixture(autouse=True)
def setup_foods(self, db):
    cache.delete(ALIAS_CACHE_KEY)
    # ... create objects ...
    cache.delete(ALIAS_CACHE_KEY)
    yield
    cache.delete(ALIAS_CACHE_KEY)
```

**What is NOT mocked:**
- Database (always real SQLite in tests)
- Django cache backend (real in-memory cache; manually invalidated)
- HTTP requests to the API (use DRF `APIClient` or `Client` directly)
- File storage (real filesystem; `STATIC_ROOT` is created if absent via `create_static_dir` fixture)

## Fixtures and Factories

**Shared fixtures (`tests/conftest.py`):**
```python
@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def user(db):
    from django.contrib.auth.models import User
    return User.objects.create_user(username="testuser", password="password")

@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    api_client.force_login(user=user)
    return api_client
```

**Session-scoped seed data:**
```python
@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "tests/data/food_fixtures.json")
```
This loads 100 food items once per test session. Tests that rely on this data use `Food.objects.first()` or `Food.objects.get(pk=1)`.

**Factory definitions (`tests/frontend/factories.py`):**
All factories use `factory.django.DjangoModelFactory` with `factory.Sequence` for unique fields:
```python
class FoodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Food

    name = factory.Sequence(lambda n: f"Food {n}")
    bls_code = factory.Sequence(lambda n: f"C{n:06d}")
    energy_in_kj_per_100g = 418.0
    energy_in_kcal_per_100g = 100.0
    protein_in_g_per_100g = 10.0
    # ... all nutrient fields with sensible defaults ...

class MealPlanDayFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MealPlanDay
    meal_plan = factory.SubFactory(MealPlanFactory)
    name = factory.Sequence(lambda n: f"Tag {n+1}")
```

**Frontend fixtures (`tests/frontend/conftest.py`):**
```python
@pytest.fixture
def logged_in_page(page: Page, live_server, test_user, test_password):
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(live_server.url + "/login/")
    page.fill("#id_username", test_user.username)
    page.fill("#id_password", test_password)
    page.click(".btn-login")
    expect(page).to_have_url(live_server.url + "/")
    return page

@pytest.fixture
def meal_plan_with_food(db):
    """Returns (plan, day, food, mpf) — a plan with a day that has one breakfast ingredient."""
    plan = MealPlanFactory()
    day = MealPlanDayFactory(meal_plan=plan)
    food = FoodFactory(name="Test Ingredient", energy_in_kcal_per_100g=200.0, ...)
    mpf = MealPlanFoodFactory(meal_plan_day=day, food=food, amount_in_g=100.0, meal_type="breakfast")
    return plan, day, food, mpf
```

**Inline helpers in test files (not fixtures):**
Tests that need one-off objects use private `_make_food()` / `_food()` helper functions within the test module rather than importing from factories:
```python
def _make_food(**kwargs):
    defaults = dict(bls_code="TEST001", name="Testfood", energy_in_kj_per_100g=100.0, ...)
    defaults.update(kwargs)
    return Food.objects.create(**defaults)
```

**Inline fixture on class:**
Real-world scenario tests use an `autouse=True` class fixture for setup:
```python
class TestRealWorldAliases:
    @pytest.fixture(autouse=True)
    def setup_foods(self, db):
        cache.delete(ALIAS_CACHE_KEY)
        self.kartoffeln = _make_food(bls_code="RW001", name="Kartoffeln")
        FoodAlias.objects.create(food=self.kartoffeln, alias="Erdäpfel")
        # ...
        yield
        cache.delete(ALIAS_CACHE_KEY)
```

**`pytest.ini` note:** `StaticFilesStorage` backend is overridden in `pytest_configure()` in `tests/conftest.py` to avoid manifest errors during tests.

## Coverage

**Requirements:** No minimum coverage enforced; no `--cov` flags in CI or `pytest.ini`.

**View Coverage:**
```bash
uv run pytest --cov=meals --cov-report=term-missing
```
(No `pytest-cov` in dependencies — must be installed separately if needed.)

## Test Types

**Unit Tests (no DB, `tests/test_*.py`):**
- Pure Python logic: `tests/test_search_utilities.py`, `tests/test_template_filters.py`, `tests/test_nutrients.py`
- Test a single function/class with no external dependencies

**Integration Tests (with DB, `tests/test_*.py`):**
- Model constraints, validation, signals: `tests/test_model_constraints.py`, `tests/test_model_validation.py`
- Food import command: `tests/test_food_import.py`
- Admin views: `tests/test_admin.py`
- All require `@pytest.mark.django_db`

**API Tests (`tests/api/`):**
- Use `authenticated_client` (DRF `APIClient` with `force_authenticate`)
- Test unauthenticated access (403), authenticated CRUD, business logic enforcement
- Each feature has a dedicated file (foods, mealplans, mealplandays, etc.)

**Frontend/E2E Tests (`tests/frontend/`):**
- Use Playwright `Page` via `logged_in_page` fixture
- Require live server (pytest-django `live_server` fixture — automatic)
- Require compiled JS (`pnpm build`) and SCSS (`build_scss`) before running
- Use CSS selector locators: `.meal-plan-row`, `#liveSearch`, `.btn-create`, `.modal-overlay`
- Use `expect(locator).to_have_count(N)` which auto-retries for async Vue updates

## Common Patterns

**Async Vue updates in Playwright:**
Use `wait_for_function` when a reactive filter may settle after DOM changes:
```python
logged_in_page.wait_for_function(
    "document.querySelectorAll('.meal-plan-row').length === 1"
)
```
Or use `expect(locator).to_have_count(N)` which auto-retries internally.

**Error Testing:**
```python
def test_unknown_nutrient_key_rejected(self):
    plan = MealPlan(thresholds={"unknown_nutrient": {"min": 10, "max": 50}})
    with pytest.raises(ValidationError, match="Invalid thresholds"):
        plan.full_clean()
```

**API error response testing:**
```python
response = authenticated_client.patch(f"/api/foods/{food.id}/", payload, format="json")
assert response.status_code == status.HTTP_400_BAD_REQUEST
assert "Cannot set both" in str(response.data)
```

**Refresh from DB after mutation:**
```python
food.refresh_from_db()
assert food.energy_in_kcal_per_100g == 200.0
```

**Unauthenticated/authenticated pattern (always test both):**
```python
def test_list_foods_unauthenticated(self, api_client):
    response = api_client.get("/api/foods/")
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_list_foods_authenticated(self, authenticated_client):
    response = authenticated_client.get("/api/foods/")
    assert response.status_code == status.HTTP_200_OK
```

**Batch factory creation:**
```python
MealPlanFactory.create_batch(12)
```

## CI Configuration

Four jobs in `.github/workflows/tests.yml`, triggered on PRs to `main`:

| Job | Command | Notes |
|-----|---------|-------|
| `lint` | `uv run black --check .` | Fails PR if formatting is wrong |
| `unit-tests` | `uv run pytest tests/test_*.py --create-db` | Unit + integration |
| `api-tests` | `uv run pytest tests/api/ --create-db` | DRF API tests |
| `frontend-tests` | `uv run pytest tests/frontend/ --create-db` | Playwright (Chromium) |

All CI jobs:
1. Install WeasyPrint system libs via apt
2. Run `pnpm install --frozen-lockfile && pnpm build`
3. `unit-tests` and `frontend-tests` also run `uv run python manage.py build_scss`
4. Frontend job installs Playwright: `uv run playwright install --with-deps chromium`
5. Publish JUnit XML results via `dorny/test-reporter`
6. Frontend failures upload screenshots and traces as artifacts (`playwright-artifacts/`)

---

*Testing analysis: 2026-03-16*
