"""Network-aware CSRF and session helpers for localhost + LAN access."""
import re

from django.conf import settings


_LAN_ORIGIN = re.compile(
    r'^https?://('
    r'localhost|127\.0\.0\.1|'
    r'192\.168\.\d{1,3}\.\d{1,3}|'
    r'10\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
    r'172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}'
    r')(:\d+)?$',
    re.I,
)


class FlexibleCsrfMiddleware:
    """Allow CSRF from localhost and private LAN origins (phones on Wi‑Fi)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.META.get('HTTP_ORIGIN', '')
        if origin and _LAN_ORIGIN.match(origin):
            trusted = list(getattr(settings, 'CSRF_TRUSTED_ORIGINS', []))
            if origin not in trusted:
                trusted.append(origin)
                settings.CSRF_TRUSTED_ORIGINS = trusted
        return self.get_response(request)
