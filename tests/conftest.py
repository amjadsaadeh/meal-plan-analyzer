import pytest
import os
from pathlib import Path
from django.core.management import call_command
from django.conf import settings

@pytest.fixture(scope='session', autouse=True)
def create_static_dir():
    static_root = Path(settings.STATIC_ROOT)
    if not static_root.exists():
        static_root.mkdir(parents=True, exist_ok=True)

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'tests/data/food_fixtures.json')

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()
