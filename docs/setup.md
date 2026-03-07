---
title: Setup & Deployment
nav_order: 2
---

# Setup & Deployment

## Local Development (SQLite)

```bash
cp .env.example .env   # fill in SECRET_KEY at minimum
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

## Docker Compose (PostgreSQL)

```bash
docker compose up
```

Spins up PostgreSQL 16 and the Django app on port 8000. Migrations and `collectstatic` run automatically.

## Environment Variables

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key |
| `DEBUG` | No | Default `False` |
| `ALLOWED_HOSTS` | No | Comma-separated; defaults to `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | No | Comma-separated HTTPS origins |
| `DATABASE_URL` | No | Default: `sqlite:///db.sqlite3`; prod: `postgres://…` |

## Food Data Import

```bash
uv run python manage.py import_foods <path/to/bls_file.xlsx>
```

## Running Tests

```bash
uv run pytest                      # full suite
uv run pytest tests/api/           # API tests only
uv run pytest tests/frontend/      # Playwright browser tests only
```

Install Playwright browsers once:

```bash
uv run playwright install --with-deps chromium
```

## Production Deployment

### Initial Database Bootstrap

```bash
cd deployment/ansible
uv run ansible-playbook --vault-id ${ANSIBLE_VAULT_ID}@vault-key-client bootstrap-databases.yml
```

### Deploy to Production

```bash
cd deployment/ansible
uv run ansible-playbook --vault-id ${ANSIBLE_VAULT_ID}@vault-key-client deploy-prod.yml \
  -e "docker_user=xxx docker_password=xxx"
```

### Deploy to Dev

```bash
cd deployment/ansible
uv run ansible-playbook --vault-id ${ANSIBLE_VAULT_ID}@vault-key-client deploy-dev.yml \
  -e "docker_user=xxx docker_password=xxx"
```
