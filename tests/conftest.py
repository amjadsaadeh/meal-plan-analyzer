import pytest
import os
from pathlib import Path
from django.core.management import call_command
from django.conf import settings
import os


def pytest_configure():
    from django.conf import settings

    settings.STORAGES["staticfiles"] = {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    }


@pytest.fixture(scope="session", autouse=True)
def create_static_dir():
    static_root = Path(settings.STATIC_ROOT)
    if not static_root.exists():
        static_root.mkdir(parents=True, exist_ok=True)


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
