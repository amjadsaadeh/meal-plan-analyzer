# Meal Plan Analyzer

A web application for meal planning and nutritional analysis based on the
[Bundeslebensmittelschlüssel (BLS)](https://www.blsdb.de/) — the German National Food Database.

## Features

- **Food Database**: Nutritional values per 100g including energy (kcal/kJ), macronutrients
  (protein, fat, carbs, fiber, sugar, n-3), vitamins (A, B1, B2, B3, B5, B6, B12, C, D),
  minerals (calcium, iron, magnesium, zinc, iodine, copper, manganese, molybdenum), and biotin
- **Custom Foods**: Create, edit, and delete user-defined food entries alongside BLS-imported data
- **Food Aliases**: Add alternative names/synonyms to any food for improved search results
- **Meal Planning**: Create multi-day meal plans with breakfast, lunch, and dinner
- **Nutritional Analysis**: Track total nutrient intake per day and across the full plan
- **Threshold Presets**: Define reusable min/max nutrient targets and get visual feedback
- **Smart Search**: Energy-intent detection, German umlaut-aware search, and alias matching
- **PDF Export**: Async background PDF generation (via Celery) with optional custom logo and footer
- **REST API**: Full CRUD operations via Django REST Framework
- **i18n**: English and German interface

## Tech Stack

- **Backend**: Django 6.0 + Django REST Framework
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: Vue 3 / Vite SPA + Django templates with SCSS
- **Async Tasks**: Celery + Redis
- **PDF**: WeasyPrint
- **Testing**: pytest + Playwright

## Local Development (SQLite)

```bash
cp .env.example .env        # set SECRET_KEY at minimum
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

### Frontend (Vue / Vite)

```bash
pnpm install
pnpm dev        # Vite dev server at :5173 (proxied when DEBUG=True)
pnpm build      # build to frontend/dist/
```

### SCSS

```bash
uv run python manage.py build_scss    # compile SCSS to sass_cache/
```

In development, `django-sass-processor` compiles SCSS on demand — no manual step needed.

## Docker Compose (PostgreSQL)

```bash
docker compose up
```

Starts PostgreSQL 16, the Django app on port 8000, and a Celery worker. Migrations and
`collectstatic` run automatically on startup.

## Import Food Data

```bash
uv run python manage.py import_foods <path/to/bls_file.xlsx>
```

## Environment Variables

Copy `.env.example` to `.env`. Key variables:

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key |
| `DEBUG` | No | Default `False` |
| `ALLOWED_HOSTS` | No | Comma-separated; defaults to `localhost,127.0.0.1` |
| `DATABASE_URL` | No | Default: `sqlite:///db.sqlite3` |
| `CELERY_BROKER_URL` | No | Default: `redis://localhost:6379/0` |
| `REDIS_URL` | No | Default: `redis://localhost:6379/1` (cache backend) |
| `SITE_BASE_URL` | No | Default: `http://localhost:8000`; used by Celery worker to resolve static/media files |

## Running the Celery Worker

```bash
uv run celery -A config worker -l info
```

## Testing

**Always format before running tests** (CI enforces Black):

```bash
uv run black . && uv run pytest              # format then run full suite
uv run pytest tests/api/                     # API tests only
uv run pytest tests/frontend/               # Playwright tests only
uv run pytest tests/test_*.py               # unit/integration tests only
uv run pytest --create-db                   # force rebuild of test database
```

First-time Playwright setup:

```bash
uv run playwright install --with-deps chromium
uv run python manage.py build_scss          # required before frontend tests
```

## Deployment

### Docker

```bash
docker compose up --build
```

### Kubernetes (via Ansible)

```bash
cd deployment/app-deployment/ansible
uv run ansible-playbook --vault-id ${ANSIBLE_VAULT_ID}@vault-key-client deploy.yml
```

Manifests live in `deployment/app-deployment/k8s/`.

## License

MIT
