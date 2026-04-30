from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.http import HttpResponse

_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 300  # 5 minutes


class ThrottledLoginView(LoginView):
    """Login view with IP-based brute-force protection backed by the Django cache."""

    def _client_ip(self):
        xff = self.request.META.get("HTTP_X_FORWARDED_FOR")
        return (
            xff.split(",")[0].strip()
            if xff
            else self.request.META.get("REMOTE_ADDR", "unknown")
        )

    def _cache_key(self):
        return f"login_attempts:{self._client_ip()}"

    def dispatch(self, request, *args, **kwargs):
        if cache.get(self._cache_key(), 0) >= _MAX_ATTEMPTS:
            return HttpResponse(
                "Too many failed login attempts. Please try again in 5 minutes.",
                status=429,
            )
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        key = self._cache_key()
        cache.set(key, cache.get(key, 0) + 1, _LOCKOUT_SECONDS)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._cache_key())
        return super().form_valid(form)
