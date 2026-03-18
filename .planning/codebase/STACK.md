# Technology Stack

**Analysis Date:** 2026-03-16

## Languages

**Primary:**
- Python 3.12 - All backend code (`config/`, `meals/`, `tests/`)
- JavaScript (ES modules) - Vue 3 frontend (`frontend/src/`)

**Secondary:**
- SCSS - Stylesheet authoring (`meals/static/meals/scss/`)
- HTML (Django template syntax with `.html.j2` extension) - Server-rendered templates (`meals/templates/meals/`)

## Runtime

**Environment:**
- Python 3.12 (pinned via `.python-version`)
- Node.js 22 (used for JS build only; declared in `Dockerfile` node-builder stage)

**Package Manager:**
- Python: `uv` (never pip). `uv.lock` is committed. Run all commands with `uv run` or `uv sync`.
- JavaScript: `pnpm` (never npm or yarn). `pnpm-lock.yaml` is committed at repo root.
- Lockfiles: both `uv.lock` and `pnpm-lock.yaml` present and committed.

## Frameworks

**Core:**
- Django 6.0 - Web framework, ORM, admin, auth, i18n (`config/settings.py`)
- Django REST Framework 3.16.1+ - REST API layer (`meals/views.py`, `meals/serializers.py`)
- Vue 3.5 - Frontend SPA components (`frontend/src/`)
- Vite 6.0 - JS build tool; four entry points built to `frontend/dist/` (`vite.config.js`)

**Testing:**
- pytest 9.0.2+ with pytest-django 4.11.1 - Test runner (`pytest.ini`)
- pytest-playwright 0.7.2 - Browser-based frontend tests
- Playwright 1.56.0 - Browser automation (Chromium only in CI)
- factory-boy 3.3.3 - Test object factories (`tests/frontend/factories.py`)

**Build/Dev:**
- django-sass-processor 1.4.2 - On-demand SCSS compilation via `{% sass_src %}` template tag
- libsass 0.23.0 - SCSS compiler used by `build_scss` management command
- django-vite 3.1.0 - Bridges Vite manifest with Django template tags
- black 26.3.0 - Code formatter (line length 88, target py312)

## Key Dependencies

**Critical:**
- `weasyprint 68.0+` - HTML→PDF generation for meal plan exports; requires system libs (libpango, libcairo, etc.)
- `psycopg[binary] 3.2.3+` - PostgreSQL adapter (binary extras for zero-build deploys)
- `django-environ 0.11.2+` - `.env` file parsing into Django settings
- `jsonschema 4.26.0+` - Validates `MealPlan.thresholds` JSON field against `THRESHOLD_SCHEMA`
- `openpyxl 3.1.5+` - Reads BLS Excel files in the `import_foods` management command
- `whitenoise 6.8.2+` - Serves static files in production (middleware + `CompressedManifestStaticFilesStorage`)

**Infrastructure:**
- `gunicorn 23.0.0+` - WSGI application server in production
- `tqdm 4.67.1+` - Progress bars in the `import_foods` management command
- `@vueuse/core 13.0` - Vue composition utilities used in frontend components
- `@vitejs/plugin-vue 5.0` - Vue SFC support in Vite

**Dev/Deployment:**
- `ansible 13.2.0+` - Kubernetes deployment automation (`deployment/app-deployment/ansible/`)
- `kubernetes 34.1.0+` - Python k8s client (used by Ansible playbooks)
- `nc-dnsapi 0.1.5+` - Netcup DNS API client for DNS automation in Ansible

## Configuration

**Environment:**
- Configured via `.env` file (parsed by `django-environ`)
- Template: `.env.example`
- Required: `SECRET_KEY`
- Optional with defaults: `DEBUG` (False), `ALLOWED_HOSTS` (localhost,127.0.0.1), `DATABASE_URL` (SQLite), `CSRF_TRUSTED_ORIGINS` (empty)
- Optional for Vite dev: `VITE_DEV_SERVER_HOST`, `VITE_ORIGIN`

**Build:**
- Python: `pyproject.toml` with hatchling build backend, version from VCS tags
- JS: `vite.config.js` — four entry points, `base: '/static/'`, output to `frontend/dist/`
- SCSS: `SASS_PROCESSOR_ROOT = BASE_DIR / 'sass_cache'` (excluded from git, populated by `build_scss` or on-demand)
- Static files storage: `whitenoise.storage.CompressedManifestStaticFilesStorage` in production; plain `FileSystemStorage` overridden in tests

## Platform Requirements

**Development:**
- Python 3.12+
- Node.js 22+ (for `pnpm dev` / `pnpm build`)
- System libraries for WeasyPrint: `libglib2.0-0`, `libpango-1.0-0`, `libharfbuzz0b`, `libpangoft2-1.0-0`, `libpangocairo-1.0-0`, `libcairo2`, `libgdk-pixbuf2.0-0`
- Chromium (for Playwright frontend tests): `uv run playwright install --with-deps chromium`

**Production:**
- Docker multi-stage build: `node:22-slim` (JS build) + `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` (Python deps) + `python:3.12-slim-bookworm` (final)
- Gunicorn on port 8000
- Kubernetes (k3s) deployment via Ansible (`deployment/app-deployment/`)
- PostgreSQL 16 (Docker Compose uses `postgres:16-alpine`)

---

*Stack analysis: 2026-03-16*
