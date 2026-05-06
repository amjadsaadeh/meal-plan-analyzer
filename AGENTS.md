# AGENTS.md — Coding Agent Guidelines for RSOS Meal Planner

## Package Manager

**Always use `uv` — never use `pip` or bare `python`.**

```bash
uv sync                    # install/sync dependencies
uv add <package>           # add dependency
uv run python manage.py …  # run Django commands
uv run pytest              # run tests
```

`uv.lock` must stay in sync with `pyproject.toml`; commit both when dependencies change.


---

## Build / Run Commands

```bash
cp .env.example .env                    # fill in SECRET_KEY
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
uv run python manage.py build_scss      # compile SCSS (required before tests)
```

---

## Test Commands

```bash
uv run pytest                                                # full suite
uv run pytest tests/api/                                     # API tests only
uv run pytest tests/frontend/                                # Playwright tests only
uv run pytest tests/api/test_foods.py                        # single file
uv run pytest tests/api/test_foods.py::TestFoodAPI           # single class
uv run pytest tests/api/test_foods.py::TestFoodAPI::test_x   # single test
uv run pytest -k "alias"                                     # pattern match
uv run pytest --create-db                                    # rebuild test DB
uv run playwright install --with-deps chromium               # first-time setup
```

Test DB is reused by default. Use `--create-db` after migration changes.
Frontend tests use `live_server` fixture; ensure system libs (WeasyPrint) are installed.


---

## Code Style

### Imports
Standard library → Third-party (Django, DRF) → Local imports.

### Naming Conventions
- **Functions/variables**: `snake_case` (`get_alias_index`, `meal_plan_day`)
- **Classes**: `PascalCase` (`MealPlanViewSet`, `FoodAlias`)
- **Constants**: `UPPER_SNAKE_CASE` (`ALIAS_CACHE_KEY`, `NUTRIENT_IDS`)
- **Model fields**: Include units (`energy_in_kcal_per_100g`)

### Formatting
Always use `black` for formatting before committing:
```bash
uv run black .
```


### Type Hints & Docstrings
```python
def get_alias_index() -> dict[int, list[str]]:
    """Return cached dict mapping food_id → list[alias_string]."""
    ...
```

Use `# ---` comment blocks to separate logical sections in longer files.

---

## Django Patterns

### Models
- Call `full_clean()` in `save()` if model has validation logic
- Use `related_name` on ForeignKeys for reverse lookups
- Order: fields → Meta → `__str__` → methods

```python
class FoodAlias(models.Model):
    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='aliases')
    alias = models.CharField(max_length=255)

    class Meta:
        unique_together = ('food', 'alias')

    def __str__(self):
        return f"{self.alias} → {self.food.name}"
```

### Views & ViewSets
- Frontend views: use `@login_required` decorator
- API ViewSets: use DRF's `ModelViewSet` (returns 403 for unauthenticated)
- Keep views thin; extract helpers to module-level functions

### Soft Deletes
Never hard-delete `MealPlanDay` objects. Filter with:
```python
MealPlanDay.objects.filter(removed=False)
```

### Cache Invalidation with Signals
```python
@receiver(post_save, sender=FoodAlias)
@receiver(post_delete, sender=FoodAlias)
def invalidate_alias_cache(sender, **kwargs):
    cache.delete(ALIAS_CACHE_KEY)
```

### Celery / Background Tasks
Used for PDF generation and long-running exports.
```bash
uv run celery -A config worker -l info
```
Define tasks in `meals/tasks.py`.


---

## Internationalization (i18n)

Default language: German. Use `gettext` (`_()`) for user-facing strings.

```python
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _

name = _("New Plan")  # views/functions

class MealType(models.TextChoices):
    BREAKFAST = "breakfast", _("Breakfast")  # models
```

---

## Testing Patterns

### Test Organization
- `tests/api/` — DRF APIClient tests
- `tests/frontend/` — Playwright browser tests
- `tests/test_*.py` — Unit/integration tests

### Test Pattern
```python
@pytest.mark.django_db
class TestFoodAPI:
    def test_list_foods_authenticated(self, authenticated_client):
        response = authenticated_client.get('/api/foods/')
        assert response.status_code == status.HTTP_200_OK
```

### Fixtures (`tests/conftest.py`)
- `api_client` — Unauthenticated APIClient
- `user` — Test user
- `authenticated_client` — Logged-in APIClient
- `logged_in_page` — Playwright Page (logged in as `testadmin`)

### Test Helper Pattern
```python
def _make_food(**kwargs):
    defaults = dict(bls_code="TEST001", name="Testfood", ...)
    defaults.update(kwargs)
    return Food.objects.create(**defaults)
```

---

## Key Files

| File | Purpose |
|------|---------|
| `meals/models.py` | Food, MealPlan, MealPlanDay, FoodAlias, signals |
| `meals/views/` | Submodules for food, mealplan, and threshold views |
| `meals/serializers.py` | DRF serializers |
| `meals/nutrients.py` | NUTRIENTS dict, THRESHOLD_SCHEMA |
| `meals/tasks.py` | Celery tasks (PDF generation, exports) |
| `meals/urls.py` | URL routing |
| `meals/admin.py` | Model registration |
| `meals/templatetags/meal_extras.py` | Custom template filters |
| `tests/conftest.py` | Shared pytest fixtures |
| `tests/frontend/factories.py` | Factory-boy definitions |
| `frontend/src/` | Vue 3 SPA components |

---

## Frontend (Vue)

**Always use `pnpm` — never `npm` or `yarn`.**

```bash
pnpm install          # install dependencies
pnpm dev              # start Vite dev server
pnpm build            # build to frontend/dist/
```

---

## Reference

For detailed technical specs (data models, API endpoints, URL maps), refer to [CLAUDE.md](file:///home/orchid/projects/meal-plan-analyzer-opencode/CLAUDE.md).



---

## Error Handling

- Use `ValidationError` for model validation with descriptive messages
- API errors handled by DRF's exception handler
- Use `get_object_or_404` for frontend views

---

## Management Commands

```bash
uv run python manage.py import_foods <xlsx/zip/url> # import food data
uv run python manage.py build_scss                 # compile SCSS
```

