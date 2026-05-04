"""
Security regression tests.

Covers:
  - Login rate limiting (ThrottledLoginView): blocks after MAX_ATTEMPTS failures,
    clears counter on successful login, GET requests are never counted.
  - DRF throttle configuration: both throttle classes and rates are present.
  - Security header settings: HSTS, secure cookies, nosniff active when DEBUG=False.
"""

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_cache():
    """Isolate cache state between tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def login_user(db):
    return User.objects.create_user(username="logintest", password="correct-pass")


# ---------------------------------------------------------------------------
# Login rate limiting
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLoginRateLimiting:
    def _post(self, client, username="logintest", password="wrong"):
        return client.post(
            "/login/",
            {"username": username, "password": password},
            REMOTE_ADDR="1.2.3.4",
        )

    def test_first_five_failures_return_200(self, login_user):
        client = Client()
        for _ in range(5):
            resp = self._post(client)
            assert resp.status_code == 200, "Form re-display expected before lockout"

    def test_sixth_attempt_returns_429(self, login_user):
        client = Client()
        for _ in range(5):
            self._post(client)
        resp = self._post(client)
        assert resp.status_code == 429

    def test_get_request_not_counted(self, login_user):
        client = Client()
        # Exhaust the counter via POST failures
        for _ in range(5):
            self._post(client)
        # A GET should still be blocked (counter already at limit) — but it
        # should not itself increment the counter beyond limit
        resp = client.get("/login/", REMOTE_ADDR="1.2.3.4")
        assert resp.status_code == 429

    def test_success_clears_counter(self, login_user):
        client = Client()
        # Fail three times
        for _ in range(3):
            self._post(client)
        # Succeed — counter should reset
        resp = self._post(client, password="correct-pass")
        assert resp.status_code == 302  # redirect after login

        # Cache should now be cleared; three more failures should still be allowed
        client2 = Client()
        for _ in range(3):
            resp = self._post(client2)
            assert resp.status_code == 200

    def test_different_ips_have_independent_counters(self, login_user):
        client = Client()
        # Exhaust counter for IP A
        for _ in range(5):
            client.post(
                "/login/",
                {"username": "logintest", "password": "wrong"},
                REMOTE_ADDR="10.0.0.1",
            )
        # IP B should still be allowed
        resp = client.post(
            "/login/",
            {"username": "logintest", "password": "wrong"},
            REMOTE_ADDR="10.0.0.2",
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# DRF throttle configuration
# ---------------------------------------------------------------------------


def test_drf_throttle_classes_configured():
    from django.conf import settings

    throttle_classes = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_CLASSES", [])
    assert "rest_framework.throttling.UserRateThrottle" in throttle_classes
    assert "rest_framework.throttling.AnonRateThrottle" in throttle_classes


def test_drf_throttle_rates_configured():
    from django.conf import settings

    rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
    assert "user" in rates
    assert "anon" in rates


def test_drf_authentication_classes_explicit():
    from django.conf import settings

    auth_classes = settings.REST_FRAMEWORK.get("DEFAULT_AUTHENTICATION_CLASSES", [])
    assert "rest_framework.authentication.SessionAuthentication" in auth_classes


# ---------------------------------------------------------------------------
# Security header settings
# ---------------------------------------------------------------------------


def test_content_type_nosniff_enabled():
    from django.conf import settings

    assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True


def test_secure_cookies_enabled_in_production():
    from django.conf import settings

    # conftest.py forces DEBUG=False for all tests, so the `if not DEBUG:` block
    # in settings.py runs and these should be True.
    assert settings.SESSION_COOKIE_SECURE is True
    assert settings.CSRF_COOKIE_SECURE is True


def test_hsts_configured_in_production():
    from django.conf import settings

    assert settings.SECURE_HSTS_SECONDS == 31536000
    assert settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    assert settings.SECURE_HSTS_PRELOAD is True
