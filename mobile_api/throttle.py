"""Small fixed-window rate limiter on Django's cache.

NOTE: the default LocMemCache is per-process. With several workers, configure a
shared cache (Redis / database cache) so limits are global.
"""
import hashlib

from django.conf import settings
from django.core.cache import cache


def client_ip(request):
    if getattr(settings, 'MOBILE_API_TRUST_PROXY_HEADER', False):
        fwd = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if fwd:
            return fwd.split(',')[-1].strip()[:45]
    return (request.META.get('REMOTE_ADDR') or 'unknown')[:45]


def _key(scope, ident):
    return 'api:rl:%s:%s' % (scope, hashlib.sha256(ident.encode()).hexdigest()[:32])


def hit(scope, ident, limit, window):
    """Count one hit. Returns (allowed, retry_after_seconds)."""
    key = _key(scope, ident)
    added = cache.add(key, 1, window)
    if added:
        return True, 0
    try:
        n = cache.incr(key)
    except ValueError:
        cache.set(key, 1, window)
        return True, 0
    return (n <= limit), window


def is_blocked(scope, ident, limit):
    return (cache.get(_key(scope, ident), 0) or 0) >= limit


def clear(scope, ident):
    cache.delete(_key(scope, ident))
