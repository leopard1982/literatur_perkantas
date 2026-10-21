class CmsNoCacheMiddleware:
    """Prevents proxies/browsers from caching authenticated CMS pages."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/cms/'):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response['Pragma'] = 'no-cache'
        return response


def describe_device(ua):
    """Ringkas user-agent menjadi 'Perangkat · OS · Browser'."""
    low = ua.lower()
    if 'okhttp' in low or 'dart' in low or 'expo' in low or 'cfnetwork' in low:
        client_hint = 'Aplikasi Mobile'
    else:
        client_hint = ''

    if 'ipad' in low or 'tablet' in low:
        kind = 'Tablet'
    elif 'mobi' in low or 'iphone' in low or ('android' in low and 'mobile' in low):
        kind = 'HP'
    else:
        kind = 'Desktop'

    if 'android' in low:
        os_name = 'Android'
    elif 'iphone' in low or 'ipad' in low or 'ios' in low:
        os_name = 'iOS'
    elif 'windows' in low:
        os_name = 'Windows'
    elif 'mac os' in low or 'macintosh' in low:
        os_name = 'macOS'
    elif 'linux' in low:
        os_name = 'Linux'
    else:
        os_name = ''

    browser = ''
    for needle, name in (('edg/', 'Edge'), ('opr/', 'Opera'), ('firefox', 'Firefox'),
                         ('samsungbrowser', 'Samsung Browser'), ('chrome', 'Chrome'),
                         ('safari', 'Safari')):
        if needle in low:
            browser = name
            break

    if client_hint and kind == 'Desktop' and not os_name:
        kind = client_hint
    parts = [kind, os_name, browser]
    return ' · '.join(p for p in parts if p)[:100] or 'Tidak diketahui'


class VisitTrackingMiddleware:
    """Mencatat pengunjung unik harian untuk website dan API mobile (untuk analitik CMS)."""

    SKIP_PREFIXES = ('/cms/', '/admin/', '/static/', '/media/', '/sitemap.xml', '/robots.txt', '/favicon')
    BOT_HINTS = ('bot', 'spider', 'crawl', 'slurp', 'preview', 'monitor')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._track(request, response)
        except Exception:
            pass
        return response

    def _track(self, request, response):
        if request.method != 'GET' or response.status_code != 200:
            return
        path = request.path
        ua = request.META.get('HTTP_USER_AGENT', '')
        if any(hint in ua.lower() for hint in self.BOT_HINTS):
            return

        if path.startswith('/api/v1/'):
            if path != '/api/v1/home/':
                return
            source = 'mobile'
        else:
            if path.startswith(self.SKIP_PREFIXES):
                return
            if 'text/html' not in response.get('Content-Type', ''):
                return
            source = 'web'

        import datetime
        import hashlib
        from django.db.models import F
        from literatur.models import SiteVisit

        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        ip = forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR', '')
        key = hashlib.sha256(f'{ip}|{ua}'.encode()).hexdigest()
        visit, created = SiteVisit.objects.get_or_create(
            source=source, visitor_key=key, date=datetime.date.today(),
            defaults={
                'ip_address': ip or None,
                'device': describe_device(ua),
                'user_agent': ua[:300],
            })
        if not created:
            SiteVisit.objects.filter(pk=visit.pk).update(hits=F('hits') + 1)
