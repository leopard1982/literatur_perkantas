from django.utils import timezone

from .models import ApiSession, hash_token, password_stamp


def authenticate_request(request):
    """Bearer-token auth only. Cookies/sessions are deliberately ignored so the
    API is not exposed to CSRF. Returns (user, session) or (None, None)."""
    header = request.META.get('HTTP_AUTHORIZATION', '')
    if not header.startswith('Bearer '):
        return None, None
    raw = header[7:].strip()
    if not raw or len(raw) > 200:
        return None, None
    try:
        session = ApiSession.objects.select_related('user').get(
            access_hash=hash_token(raw),
            revoked_at__isnull=True,
        )
    except ApiSession.DoesNotExist:
        return None, None
    now = timezone.now()
    user = session.user
    if session.access_expires_at <= now or not user.is_active:
        return None, None
    if session.pw_stamp != password_stamp(user):
        return None, None
    # cheap, throttled "last seen" update (at most once a minute per session)
    if session.last_used_at is None or (now - session.last_used_at).total_seconds() > 60:
        ApiSession.objects.filter(pk=session.pk).update(last_used_at=now)
    return user, session
