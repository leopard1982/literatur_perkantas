import functools
import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from . import throttle
from .auth import authenticate_request

log = logging.getLogger('mobile_api')

MAX_BODY_BYTES = 8 * 1024
MAX_UPLOAD_BYTES = 6 * 1024 * 1024


def error(status, code, message, **headers):
    resp = JsonResponse({'error': {'code': code, 'message': message}}, status=status)
    for k, v in headers.items():
        resp[k.replace('_', '-')] = str(v)
    return resp


def _harden(resp, private):
    resp['X-Content-Type-Options'] = 'nosniff'
    resp['Referrer-Policy'] = 'no-referrer'
    resp['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'"
    resp['X-Frame-Options'] = 'DENY'
    if private:
        resp['Cache-Control'] = 'private, no-store'
        resp['Pragma'] = 'no-cache'
    elif 'Cache-Control' not in resp:
        resp['Cache-Control'] = 'no-cache'
    # responses can differ per Authorization header
    resp['Vary'] = 'Authorization, Accept-Encoding'
    return resp


def api(methods, auth='none', rate=(120, 60), cache_seconds=0, multipart=False):
    """Wrap a JSON endpoint.

    auth: 'none' | 'optional' | 'required'  (Bearer token only, never cookies)
    rate: (max requests, window seconds) per client IP
    cache_seconds: public max-age for anonymous GETs (private/no-store otherwise)
    multipart: also accept multipart/form-data uploads (up to MAX_UPLOAD_BYTES)
    """
    methods = [m.upper() for m in methods]

    def deco(view):
        @csrf_exempt
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method not in methods:
                return _harden(error(405, 'method_not_allowed', 'Metode tidak diizinkan.',
                                     Allow=', '.join(methods)), True)
            allowed, retry = throttle.hit('ip:' + view.__name__, throttle.client_ip(request), rate[0], rate[1])
            if not allowed:
                return _harden(error(429, 'rate_limited', 'Terlalu banyak permintaan, coba lagi nanti.',
                                     Retry_After=retry), True)

            request.api_user, request.api_session = None, None
            has_token = bool(request.META.get('HTTP_AUTHORIZATION'))
            if auth in ('required', 'optional'):
                request.api_user, request.api_session = authenticate_request(request)
                if auth == 'required' and request.api_user is None:
                    return _harden(error(401, 'unauthorized', 'Sesi tidak valid atau sudah berakhir.',
                                         WWW_Authenticate='Bearer'), True)

            request.json = {}
            if request.method in ('POST', 'PUT', 'PATCH'):
                ctype = (request.META.get('CONTENT_TYPE') or '').split(';')[0].strip().lower()
                length = int(request.META.get('CONTENT_LENGTH') or 0)
                is_upload = multipart and ctype == 'multipart/form-data'
                if length > (MAX_UPLOAD_BYTES if is_upload else MAX_BODY_BYTES):
                    return _harden(error(413, 'too_large', 'Permintaan terlalu besar.'), True)
                if length and not is_upload:
                    if ctype != 'application/json':
                        return _harden(error(415, 'unsupported_media_type', 'Gunakan application/json.'), True)
                    try:
                        data = json.loads(request.body[:MAX_BODY_BYTES].decode('utf-8'))
                    except (ValueError, UnicodeDecodeError):
                        return _harden(error(400, 'bad_json', 'Format JSON tidak valid.'), True)
                    if not isinstance(data, dict):
                        return _harden(error(400, 'bad_json', 'Body harus berupa objek JSON.'), True)
                    request.json = data

            try:
                resp = view(request, *args, **kwargs)
            except Exception:
                log.exception('unhandled error in %s', view.__name__)
                return _harden(error(500, 'server_error', 'Terjadi kesalahan pada server.'), True)

            public = (request.method == 'GET' and cache_seconds and request.api_user is None and not has_token)
            _harden(resp, private=not public)
            if public:
                resp['Cache-Control'] = 'public, max-age=%d' % cache_seconds
            return resp
        return wrapper
    return deco
