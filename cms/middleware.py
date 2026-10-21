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

        ip = request.META.get('REMOTE_ADDR', '')
        key = hashlib.sha256(f'{ip}|{ua}'.encode()).hexdigest()
        visit, created = SiteVisit.objects.get_or_create(
            source=source, visitor_key=key, date=datetime.date.today())
        if not created:
            SiteVisit.objects.filter(pk=visit.pk).update(hits=F('hits') + 1)
