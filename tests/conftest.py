import json
import pytest
import os
from pathlib import Path
from django.core.management import call_command
from django.conf import settings
import os

# Vite entry points referenced by Django templates.
_VITE_ENTRIES = [
    "frontend/src/mealplan-list/main.js",
    "frontend/src/mealplan-detail/main.js",
    "frontend/src/food-database/main.js",
    "frontend/src/food-editor/main.js",
    "frontend/src/threshold-preset-list/main.js",
    "frontend/src/threshold-preset-editor/main.js",
]


def _ensure_vite_manifest():
    """Create a minimal Vite manifest so template tests can render without pnpm build."""
    base_dir = Path(__file__).resolve().parent.parent
    manifest_path = base_dir / "frontend" / "dist" / ".vite" / "manifest.json"
    if manifest_path.exists():
        return  # Real build artifact present – don't overwrite.
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        entry: {
            "file": f"assets/{entry.split('/')[-2]}-main.js",
            "src": entry,
            "isEntry": True,
        }
        for entry in _VITE_ENTRIES
    }
    manifest_path.write_text(json.dumps(manifest))


def pytest_configure():
    # Create the Vite manifest BEFORE Django initialises so that django_vite
    # reads it correctly on first load (the loader caches the manifest once).
    _ensure_vite_manifest()

    from django.conf import settings

    settings.STORAGES["staticfiles"] = {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    }
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }


@pytest.fixture(scope="session", autouse=True)
def create_static_dir():
    static_root = Path(settings.STATIC_ROOT)
    if not static_root.exists():
        static_root.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session", autouse=True)
def reset_vite_loader():
    """Reset the DjangoViteAssetLoader singleton so it re-reads the manifest
    that _ensure_vite_manifest() created during pytest_configure."""
    try:
        from django_vite.core.asset_loader import DjangoViteAssetLoader

        DjangoViteAssetLoader._instance = None
    except ImportError:
        pass


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "tests/data/food_fixtures.json")


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
