import hashlib
import secrets
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

ACCESS_TTL = getattr(settings, 'MOBILE_API_ACCESS_TTL_SECONDS', 15 * 60)
REFRESH_TTL = getattr(settings, 'MOBILE_API_REFRESH_TTL_SECONDS', 30 * 24 * 3600)


def hash_token(raw):
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def password_stamp(user):
    """Changes whenever the user's password changes -> old tokens die."""
    return hashlib.sha256(('stamp:' + user.password).encode('utf-8')).hexdigest()[:32]


class ApiSession(models.Model):
    """One row per logged-in device. Only SHA-256 hashes of tokens are stored,
    so a database leak does not leak usable tokens."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_sessions')
    access_hash = models.CharField(max_length=64, unique=True)
    refresh_hash = models.CharField(max_length=64, unique=True)
    prev_refresh_hash = models.CharField(max_length=64, blank=True, default='', db_index=True)
    access_expires_at = models.DateTimeField()
    refresh_expires_at = models.DateTimeField()
    pw_stamp = models.CharField(max_length=32)
    device_name = models.CharField(max_length=80, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'revoked_at'])]

    def rotate(self):
        """Issue a fresh access+refresh pair. Returns the raw tokens (shown once)."""
        access = secrets.token_urlsafe(48)
        refresh = secrets.token_urlsafe(48)
        now = timezone.now()
        self.prev_refresh_hash = self.refresh_hash
        self.access_hash = hash_token(access)
        self.refresh_hash = hash_token(refresh)
        self.access_expires_at = now + timezone.timedelta(seconds=ACCESS_TTL)
        self.refresh_expires_at = now + timezone.timedelta(seconds=REFRESH_TTL)
        self.pw_stamp = password_stamp(self.user)
        return access, refresh

    @classmethod
    def start(cls, user, device_name=''):
        s = cls(user=user, device_name=device_name[:80])
        # placeholders so unique constraints hold until rotate() fills real values
        s.refresh_hash = hash_token(secrets.token_urlsafe(16))
        access, refresh = s.rotate()
        s.prev_refresh_hash = ''
        s.save()
        return s, access, refresh

    def revoke(self):
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=['revoked_at'])
