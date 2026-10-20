"""Access control in front of /media/.

Before this, django.views.static.serve exposed everything under media/ to anyone:
every page image of paid books (UUIDs are public in the catalog), payment
receipts and donation receipts. Rules now:

* extract/pdf_full/<book>/<n>.jpg : pages 1-5 public (cover + the same 5-page
  preview the website already offers); later pages only for free books, owners
  of the book, or staff.
* bukti_bayar/*  : the payer or staff.
* donation/*, pdf_full/* : staff only.
* everything else (covers of categories, blog images, ...) stays public.
"""
import re
import uuid

from django.conf import settings
from django.http import Http404, HttpResponseForbidden
from django.views.static import serve

from mobile_api.auth import authenticate_request

from .models import Books, MyPayment, UserBook

PREVIEW_PAGES = 5
PAGE_RE = re.compile(r'^extract/pdf_full/([0-9a-fA-F-]{36})/(\d{1,5})\.jpg$')


def _user(request):
    """Browser session user, or the mobile app's Bearer-token user."""
    if request.user.is_authenticated:
        return request.user
    user, _ = authenticate_request(request)
    return user


def _deny(request):
    resp = HttpResponseForbidden('Forbidden')
    resp['Cache-Control'] = 'private, no-store'
    return resp


def protected_media(request, path):
    path = path.lstrip('/')
    if '..' in path.split('/') or '\x00' in path:
        raise Http404()

    root = path.split('/', 1)[0]
    user = None
    private = False

    if root == 'extract':
        m = PAGE_RE.match(path)
        if not m:
            raise Http404()
        try:
            book_id = uuid.UUID(m.group(1))
        except ValueError:
            raise Http404()
        page = int(m.group(2))
        if page > PREVIEW_PAGES:
            private = True
            user = _user(request)
            book = Books.objects.filter(id=book_id).values('kategori_id').first()
            if book is None:
                raise Http404()
            allowed = (
                book['kategori_id'] == 3
                or (user is not None and (
                    user.is_staff
                    or UserBook.objects.filter(id_user=user, id_book_id=book_id).exists()))
            )
            if not allowed:
                return _deny(request)
    elif root == 'bukti_bayar':
        private = True
        user = _user(request)
        if user is None or not (user.is_staff or MyPayment.objects.filter(bukti=path, user=user).exists()):
            return _deny(request)
    elif root in ('donation', 'pdf_full'):
        private = True
        user = _user(request)
        if user is None or not user.is_staff:
            return _deny(request)

    resp = serve(request, path, document_root=settings.MEDIA_ROOT)
    resp['X-Content-Type-Options'] = 'nosniff'
    if private:
        resp['Cache-Control'] = 'private, max-age=3600'
    return resp
