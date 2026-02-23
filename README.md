# RSOS Meal Planner

A web application for meal planning and nutritional analysis based on the
[Bundeslebensmittelschlüssel (BLS)](https://www.blsdb.de/) — the German National Food Database.

## Features

- **Food Database**: Nutritional values per 100g including energy (kcal/kJ), macronutrients
  (protein, fat, carbs, fiber, sugar, omega-3), vitamins (A, B12, C, D), and minerals
  (calcium, iron, magnesium, zinc)
- **Meal Planning**: Create multi-day meal plans with breakfast, lunch, and dinner
- **Nutritional Analysis**: Track total nutrient intake per day and per meal plan
- **Threshold Presets**: Define minimum/maximum nutrient targets and get visual feedback
- **Smart Search**: German umlaut-aware food search with alias support
- **PDF Export**: Generate printable meal plans with optional custom logo
- **REST API**: Full CRUD operations via Django REST Framework

## Tech Stack

- **Backend**: Django 6.0 + Django REST Framework
- **Database**: PostgreSQL
- **Frontend**: Django templates with SCSS
- **PDF**: WeasyPrint
- **Testing**: pytest + Playwright

## Setup

```bash
cp .env.example .env
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

## Import Food Data

```bash
uv run python manage.py import_foods <xlsx_file>
```

## Testing

```bash
uv run pytest                                    # full suite
uv run pytest tests/api/                         # API tests only
uv run pytest tests/frontend/                    # Playwright tests only
uv run playwright install --with-deps chromium   # first-time setup
```

## Deployment

### Production

```bash
cd deployment/ansible
uv run ansible-playbook --vault-id ${ANSIBLE_VAULT_ID}@vault-key-client deploy-prod.yml \
  -e "docker_user=xxx docker_password=xxx"
```

### Dev (Feature Branches)

Maintainers can deploy a PR for testing by commenting `/deploy` on the PR.

The preview will be available at: `https://{branch}.mealplanalyzer-dev.{tld}`

Cleanup is automatic when the PR is closed or merged.

### Manual Dev Deployment

```bash
cd deployment/ansible
uv run ansible-playbook --vault-id ${ANSIBLE_VAULT_ID}@vault-key-client deploy-dev.yml \
  -e "branch=feature-x"
```

## License

MIT
