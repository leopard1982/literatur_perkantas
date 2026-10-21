import datetime
import json
import os
import urllib.parse
import urllib.request
import uuid

from django.contrib.auth import authenticate
from django.core import signing
from django.core.cache import cache
from django.core.paginator import EmptyPage, Paginator
from django.db import transaction
from django.db.models import Count, F, Q
from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.gzip import gzip_page

from literatur.models import (
    Blogs, BlogComment, MobileBroadcast, BookComment, Books, Category, FeaturedBook, Instagram,
    MyCart, MyPaymentDetail, inboxMessage, MyWishlist, OnSaleBook, PageReview, Pengumuman,
    UserBook,
)

from literatur.invoice import get_downloadable_payment, invoice_id_from_text, invoice_response
from literatur.models import MyPayment

from . import throttle
from .core import api, error
from .models import (
    ACCESS_TTL, BOOKMARK_COLORS, ApiSession, ReaderBookmark, ReadingPlan, ReadingProgress,
    hash_token, password_stamp,
)
from .serializers import (
    active_sale, blog_dict, book_dict, cover, media, person_name, plain_text,
    safe_https,
)

DEFAULT_PENGUMUMAN = "Selamat Datang Di Website Literatur Perkantas Nasional!"
HOME_CACHE_KEY = 'api:home:v1'
HOME_CACHE_TTL = 60
MAX_SESSIONS_PER_USER = 10
RECAPTCHA_ACTION = 'login'
RECAPTCHA_VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'


RECAPTCHA_ACTIONS = ('login', 'comment', 'bookmark')


def _recaptcha_ok(token, ip, action=RECAPTCHA_ACTION):
    """Server-side reCAPTCHA v3 check (same keys / min score as the website). Fails closed."""
    if not getattr(settings, 'MOBILE_LOGIN_RECAPTCHA', True):
        return True
    if not isinstance(token, str) or not token or len(token) > 4096:
        return False
    body = urllib.parse.urlencode({'secret': settings.RECAPTCHA_PRIVATE_KEY, 'response': token,
                                   'remoteip': ip or ''}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(RECAPTCHA_VERIFY_URL, data=body), timeout=5) as r:
            res = json.loads(r.read().decode('utf-8'))
    except Exception:
        return False
    return bool(res.get('success')) and res.get('action') == action \
        and float(res.get('score', 0)) >= getattr(settings, 'RECAPTCHA_REQUIRED_SCORE', 0.5)


def recaptcha_page(request):
    """Tiny page loaded in a hidden WebView by the app (must be served from our own origin so the
    site key's domain check passes). It hands the v3 token to the app via the `Captcha` channel."""
    action = request.GET.get('action', RECAPTCHA_ACTION)
    if action not in RECAPTCHA_ACTIONS:
        action = RECAPTCHA_ACTION
    html = (
        '<!doctype html><meta charset="utf-8"><title>captcha</title>'
        '<script src="https://www.google.com/recaptcha/api.js?render=%(k)s"></script>'
        '<script>grecaptcha.ready(function(){grecaptcha.execute("%(k)s",{action:"%(a)s"})'
        '.then(function(t){Captcha.postMessage(t)},function(){Captcha.postMessage("")})});</script>'
    ) % {'k': settings.RECAPTCHA_PUBLIC_KEY, 'a': action}
    resp = HttpResponse(html, content_type='text/html; charset=utf-8')
    resp['Content-Security-Policy'] = ("default-src 'none'; script-src 'unsafe-inline' https://www.google.com "
                                       "https://www.gstatic.com; frame-src https://www.google.com; "
                                       "connect-src https://www.google.com; frame-ancestors 'none'")
    resp['Cache-Control'] = 'no-store'
    resp['X-Content-Type-Options'] = 'nosniff'
    return resp

LOGIN_FAIL_LIMIT = 5
LOGIN_FAIL_WINDOW = 15 * 60


def _uuid_or_none(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _books_qs():
    return (Books.objects.filter(is_active=True).select_related('kategori', 'onsalebook')
            .annotate(jumlah_dibeli=Count('userbook', distinct=True)))


# ----------------------------------------------------------------- public

def _build_home():
    today = datetime.date.today()
    books = _books_qs()
    on_sale = (OnSaleBook.objects.filter(is_active=True, end_date__gte=today, book__is_active=True)
               .select_related('book__kategori')
               .annotate(jumlah_dibeli=Count('book__userbook', distinct=True))
               .order_by('-updated_at'))
    sale_list = list(on_sale[:4])

    featured = (FeaturedBook.objects.filter(is_active=True, start_date__lte=today, end_date__gte=today, book__is_active=True)
                .select_related('book__kategori').order_by('-updated_at')[:4])
    reviews = (PageReview.objects.filter(is_active=True)
               .select_related('user__userdetail').order_by('-updated_at')[:10])

    return {
        'pengumuman': (Pengumuman.objects.order_by('-id').values_list('pengumuman', flat=True).first()
                       or DEFAULT_PENGUMUMAN),
        'featured': [{'header': f.header, 'body': f.body, 'book_id': str(f.book_id),
                      'cover': cover(f.book_id)} for f in featured],
        'best_seller': [book_dict(b) for b in
                        books.filter(is_best_seller=True).exclude(kategori_id=3).order_by('-updated_at')[:6]],
        'promo_spotlight': [{
            'header': s.header, 'body': s.body, 'discount': float(s.discount),
            'nett_price': int(s.nett_price), 'end_date': s.end_date.isoformat(),
            'book': book_dict(s.book, s.jumlah_dibeli),
        } for s in sale_list],
        'new_books': [book_dict(b) for b in books.order_by('-updated_at')[:4]],
        'promo_books': [book_dict(s.book, s.jumlah_dibeli) for s in sale_list],
        'jml_on_sale': on_sale.count(),
        'free_books': [book_dict(b) for b in books.filter(kategori_id=3).order_by('-updated_at')[:12]],
        'blogs': [blog_dict(b) for b in
                  Blogs.objects.filter(is_active=True).select_related('author__userdetail')
                  .order_by('-created_at')[:4]],
        'reviews': [{'name': person_name(r.user), 'review': r.review or '',
                     'date': r.updated_at.isoformat()} for r in reviews],
        'instagram': [{'image': media(i.gambar.name), 'link': safe_https(i.link)}
                      for i in Instagram.objects.filter(is_active=True).order_by('-id')[:6]],
    }


@gzip_page
@api(['GET'], auth='optional', rate=(120, 60), cache_seconds=60)
def home(request):
    data = cache.get(HOME_CACHE_KEY)
    if data is None:
        data = _build_home()
        cache.set(HOME_CACHE_KEY, data, HOME_CACHE_TTL)
    data = dict(data)  # never mutate the cached object
    user = request.api_user
    if user is not None:
        owned = UserBook.objects.filter(id_user=user).select_related('id_book__kategori', 'id_book__onsalebook') \
            .order_by('-id')
        owned_list = list(owned[:4])
        data['owned_book_ids'] = [str(i) for i in
                                  UserBook.objects.filter(id_user=user).values_list('id_book_id', flat=True)]
        data['koleksiku'] = [book_dict(u.id_book, 0) for u in owned_list]
        data['jml_koleksiku'] = len(data['owned_book_ids'])
    return JsonResponse(data)


@gzip_page
@api(['GET'], auth='optional', rate=(180, 60))
def book_list(request):
    try:
        k = int(request.GET.get('k', 0))
    except ValueError:
        k = 0
    try:
        limit = int(request.GET.get('limit', 10))
    except ValueError:
        limit = 10
    if limit not in (10, 25, 50):
        limit = 10
    try:
        page_no = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page_no = 1
    q = (request.GET.get('q') or '').strip()[:60]

    qs = _books_qs()
    title = 'Semua Buku'
    if k == 10:
        qs, title = qs.filter(is_best_seller=True).order_by('-updated_at'), 'Buku Best Seller'
    elif k == 11:
        qs, title = qs.order_by('-created_at'), 'Buku Terbaru'
    elif k == 12:
        qs = qs.filter(onsalebook__is_active=True, onsalebook__end_date__gte=datetime.date.today()) \
               .order_by('-onsalebook__updated_at', '-updated_at')
        title = 'Buku Promo'
    elif 0 < k < 10:
        cat = Category.objects.filter(id=k).first()
        if cat:
            qs, title = qs.filter(kategori=cat).order_by('-updated_at'), cat.nama
        else:
            qs = qs.order_by('-updated_at')
    else:
        qs = qs.order_by('-updated_at')
    if q:
        qs = qs.filter(Q(judul__icontains=q) | Q(pengarang__icontains=q))

    paginator = Paginator(qs, limit)
    try:
        page = paginator.page(page_no)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    data = {
        'title': title, 'page': page.number, 'num_pages': paginator.num_pages,
        'total': paginator.count, 'results': [book_dict(b) for b in page.object_list],
        # k 1..9 = kategori (lihat cabang filter di atas); dipakai app untuk chip filter
        'categories': [{'id': c.id, 'nama': c.nama} for c in Category.objects.filter(id__range=(1, 9)).order_by('id')],
    }
    if request.api_user is not None:
        ids = [b.id for b in page.object_list]
        data['owned_book_ids'] = [str(i) for i in UserBook.objects.filter(
            id_user=request.api_user, id_book__in=ids).values_list('id_book_id', flat=True)]
    return JsonResponse(data)


@gzip_page
@api(['GET'], auth='optional', rate=(180, 60))
def book_detail(request, book_id):
    uid = _uuid_or_none(book_id)
    user = request.api_user
    # nonaktif = tidak tampil di katalog; hanya pemiliknya yang masih bisa membukanya
    book = (Books.objects.select_related('kategori', 'onsalebook')
            .annotate(jumlah_dibeli=Count('userbook', distinct=True)).filter(id=uid).first()) if uid else None
    if book is not None and not book.is_active:
        if user is None or not UserBook.objects.filter(id_user=user, id_book=book).exists():
            book = None
    if book is None:
        return error(404, 'not_found', 'Buku tidak ditemukan.')
    data = book_dict(book)
    data.update({
        'isbn': book.isbn, 'deskripsi': plain_text(book.deskripsi), 'sinopsis': plain_text(book.sinopsis),
        'owned': False, 'in_cart': False, 'in_wishlist': False, 'can_comment': book.kategori_id == 3,
    })
    if user is not None:
        data['owned'] = UserBook.objects.filter(id_user=user, id_book=book).exists()
        data['in_cart'] = MyCart.objects.filter(user=user, book=book).exists()
        data['in_wishlist'] = MyWishlist.objects.filter(user=user, book=book).exists()
        data['can_comment'] = data['owned'] or data['is_free']
        prog = ReadingProgress.objects.filter(user=user, book=book).values_list('page', flat=True).first()
        data['last_page'] = prog or 0
    comments = (BookComment.objects.filter(book=book, is_active=True, is_publish=True)
                .select_related('user__userdetail').order_by('-created_at')[:20])
    data['comments'] = [{'name': person_name(c.user), 'comment': c.comment,
                         'date': c.created_at.isoformat()} for c in comments]
    return JsonResponse(data)


@gzip_page
@api(['GET'], rate=(120, 60), cache_seconds=30)
def blog_list(request):
    try:
        page_no = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page_no = 1
    qs = Blogs.objects.filter(is_active=True).select_related('author__userdetail').order_by('-created_at')
    q = (request.GET.get('q') or '').strip()[:60]
    if q:
        qs = qs.filter(Q(header__icontains=q) | Q(body__icontains=q))
    # rentang tanggal (YYYY-MM-DD), keduanya inklusif
    for param, lookup in (('date_from', 'created_at__date__gte'), ('date_to', 'created_at__date__lte')):
        try:
            qs = qs.filter(**{lookup: datetime.date.fromisoformat(request.GET.get(param, ''))})
        except ValueError:
            pass
    paginator = Paginator(qs, 8)
    try:
        page = paginator.page(page_no)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    return JsonResponse({'page': page.number, 'num_pages': paginator.num_pages,
                         'results': [blog_dict(b) for b in page.object_list]})


@gzip_page
@api(['GET'], rate=(120, 60), cache_seconds=30)
def blog_detail(request, blog_id):
    uid = _uuid_or_none(blog_id)
    blog = (Blogs.objects.filter(id=uid, is_active=True).select_related('author__userdetail').first()
            if uid else None)
    if blog is None:
        return error(404, 'not_found', 'Artikel tidak ditemukan.')
    Blogs.objects.filter(pk=blog.pk).update(view=F('view') + 1)
    data = blog_dict(blog, full=True)
    comments = (BlogComment.objects.filter(blog=blog, is_active=True, is_publish=True)
                .select_related('user__userdetail').order_by('-created_at')[:20])
    data['comments'] = [{'name': person_name(c.user), 'comment': c.comment,
                         'date': c.created_at.isoformat()} for c in comments]
    return JsonResponse(data)


# ------------------------------------------------------------------- auth

def _token_payload(session, access, refresh):
    return {'access_token': access, 'refresh_token': refresh, 'token_type': 'Bearer',
            'expires_in': ACCESS_TTL}


@api(['POST'], rate=(30, 15 * 60))
def login(request):
    username = request.json.get('username')
    password = request.json.get('password')
    device = request.json.get('device_name', '')
    if not (isinstance(username, str) and isinstance(password, str)) or not username or not password \
            or len(username) > 150 or len(password) > 128:
        return error(400, 'invalid_input', 'Username dan password wajib diisi.')
    device = device[:80] if isinstance(device, str) else ''

    if not _recaptcha_ok(request.json.get('recaptcha_token'), throttle.client_ip(request)):
        return error(400, 'captcha_failed', 'Verifikasi reCAPTCHA gagal, silakan coba lagi.')

    ident = username.strip().lower()
    if throttle.is_blocked('login-user', ident, LOGIN_FAIL_LIMIT):
        return error(429, 'locked', 'Terlalu banyak percobaan gagal. Coba lagi dalam 15 menit.',
                     Retry_After=LOGIN_FAIL_WINDOW)

    user = authenticate(username=username.strip(), password=password)
    if user is None or not user.is_active or not hasattr(user, 'userdetail'):
        throttle.hit('login-user', ident, LOGIN_FAIL_LIMIT, LOGIN_FAIL_WINDOW)
        # identical message whether the account exists or not
        return error(401, 'invalid_credentials', 'Username atau password tidak sesuai.')

    throttle.clear('login-user', ident)
    with transaction.atomic():
        live = ApiSession.objects.filter(user=user, revoked_at__isnull=True).order_by('-created_at')
        for old in list(live)[MAX_SESSIONS_PER_USER - 1:]:
            old.revoke()
        session, access, refresh = ApiSession.start(user, device)
    payload = _token_payload(session, access, refresh)
    payload['user'] = _me(user)
    return JsonResponse(payload)


@api(['POST'], rate=(60, 60))
def refresh(request):
    raw = request.json.get('refresh_token')
    if not isinstance(raw, str) or not raw or len(raw) > 200:
        return error(400, 'invalid_input', 'refresh_token wajib diisi.')
    h = hash_token(raw)
    with transaction.atomic():
        session = (ApiSession.objects.select_for_update().select_related('user')
                   .filter(refresh_hash=h).first())
        if session is None:
            # A rotated-out refresh token being replayed means it was stolen:
            # kill the whole session so neither party keeps access.
            reused = ApiSession.objects.filter(prev_refresh_hash=h, revoked_at__isnull=True).first()
            if reused:
                reused.revoke()
            return error(401, 'unauthorized', 'Sesi tidak valid, silakan login ulang.')
        from django.utils import timezone
        if (session.revoked_at or session.refresh_expires_at <= timezone.now()
                or not session.user.is_active or session.pw_stamp != password_stamp(session.user)):
            return error(401, 'unauthorized', 'Sesi tidak valid, silakan login ulang.')
        access, new_refresh = session.rotate()
        session.save()
    return JsonResponse(_token_payload(session, access, new_refresh))


@api(['POST'], auth='required', rate=(60, 60))
def logout(request):
    request.api_session.revoke()
    return JsonResponse({'ok': True})


@api(['POST'], auth='required', rate=(20, 60))
def logout_all(request):
    for s in ApiSession.objects.filter(user=request.api_user, revoked_at__isnull=True):
        s.revoke()
    return JsonResponse({'ok': True})


# ----------------------------------------------------------------- account

def _me(user):
    d = user.userdetail
    return {
        'nama_lengkap': d.nama_lengkap or '', 'alias': d.alias or '', 'email': user.email,
        'photo': media(d.photo.name) if d.photo else None,
        'total_book': d.total_book, 'total_poin': d.total_poin,
        'jml_cart': MyCart.objects.filter(user=user).count(),
        'jml_wishlist': MyWishlist.objects.filter(user=user).count(),
        'jml_inbox': inboxMessage.objects.filter(user=user).count(),
    }


@api(['GET'], auth='required', rate=(120, 60))
def me(request):
    return JsonResponse(_me(request.api_user))


@api(['POST'], auth='required', rate=(20, 60), multipart=True)
def me_update(request):
    """Ubah nama lengkap dan/atau foto profil (multipart: nama_lengkap, photo)."""
    from io import BytesIO
    from django.core.files.base import ContentFile
    from PIL import Image, ImageOps

    d = request.api_user.userdetail
    data = request.POST if request.content_type == 'multipart/form-data' else request.json
    nama = data.get('nama_lengkap')
    photo = request.FILES.get('photo') if request.content_type == 'multipart/form-data' else None

    if nama is None and photo is None:
        return error(400, 'invalid_input', 'Tidak ada data yang diubah.')
    if nama is not None:
        nama = ' '.join(str(nama).split())
        if not nama or len(nama) > 200:
            return error(400, 'invalid_input', 'Nama wajib diisi (maksimal 200 karakter).')

    content = None
    if photo is not None:
        try:
            img = Image.open(photo)
            img.verify()
            photo.seek(0)
            img = ImageOps.exif_transpose(Image.open(photo)).convert('RGB')
            img.thumbnail((600, 600))
            buf = BytesIO()
            img.save(buf, 'JPEG', quality=85, optimize=True)
            content = ContentFile(buf.getvalue())
        except Exception:
            return error(400, 'invalid_image', 'File foto tidak valid. Gunakan JPG atau PNG.')

    if nama is not None:
        d.nama_lengkap = nama
    if content is not None:
        old = d.photo.name if d.photo else ''
        d.photo.save(f'{uuid.uuid4()}.jpg', content, save=False)
        if old.startswith('profile/'):
            try:
                d.photo.storage.delete(old)
            except Exception:
                pass
    d.save()
    return JsonResponse(_me(request.api_user))


@gzip_page
@api(['GET'], auth='required', rate=(120, 60))
def collection(request):
    rows = (UserBook.objects.filter(id_user=request.api_user)
            .select_related('id_book__kategori', 'id_book__onsalebook').order_by('-id'))
    return JsonResponse({'results': [dict(book_dict(u.id_book, 0), last_page=u.last_page) for u in rows]})


def _saved_books(request, model):
    rows = (model.objects.filter(user=request.api_user, book__isnull=False)
            .select_related('book__kategori', 'book__onsalebook').order_by('-id'))
    return JsonResponse({'results': [book_dict(r.book, 0) for r in rows]})


@api(['GET'], auth='none', rate=(120, 60))
def announcements(request):
    """Public pengumuman/promo broadcasts for the app's background poll (newest 20 active)."""
    rows = MobileBroadcast.objects.filter(is_active=True)[:20]
    return JsonResponse({'results': [{'id': b.id, 'jenis': b.jenis, 'header': b.header, 'body': b.body,
                                      'created_at': b.created_at.isoformat()} for b in rows]})


@gzip_page
@api(['GET'], auth='required', rate=(120, 60))
def my_wishlist(request):
    return _saved_books(request, MyWishlist)


@gzip_page
@api(['GET'], auth='required', rate=(120, 60))
def my_cart(request):
    return _saved_books(request, MyCart)


@api(['GET'], auth='required', rate=(120, 60))
def inbox(request):
    rows = list(inboxMessage.objects.filter(user=request.api_user).order_by('-id')[:50])
    results = []
    for m in rows:
        item = {'id': m.id, 'header': m.header, 'body': m.body,
                'created_at': m.created_at.isoformat(), 'invoice_id': None}
        if m.header == 'Pembayaran Selesai Dikonfirmasi':
            payment = get_downloadable_payment(request.api_user, invoice_id_from_text(m.body))
            if payment:
                item['invoice_id'] = payment.payment
        results.append(item)
    return JsonResponse({'results': results})


INVOICE_LINK_SALT = 'mobile-invoice-link'
INVOICE_LINK_TTL = 300  # detik


@api(['GET'], auth='required', rate=(30, 60))
def invoice_link(request, payment_id):
    """Tautan unduh sementara, supaya browser/pengunduh Android tidak perlu header Bearer."""
    payment = get_downloadable_payment(request.api_user, payment_id)
    if payment is None:
        return error(404, 'not_found', 'Invoice tidak ditemukan atau pembayaran belum disetujui.')
    token = signing.dumps(payment.payment, salt=INVOICE_LINK_SALT)
    return JsonResponse({'url': f'/api/v1/invoices/dl/{token}/', 'expires_in': INVOICE_LINK_TTL})


@api(['GET'], auth='none', rate=(30, 60))
def invoice_download(request, token):
    try:
        payment_id = signing.loads(token, salt=INVOICE_LINK_SALT, max_age=INVOICE_LINK_TTL)
    except signing.BadSignature:
        return error(404, 'not_found', 'Tautan invoice tidak valid atau sudah kedaluwarsa.')
    payment = MyPayment.objects.filter(payment=payment_id, is_verified=True).first()
    if payment is None:
        return error(404, 'not_found', 'Invoice tidak ditemukan.')
    return invoice_response(payment)


@api(['GET'], auth='required', rate=(30, 60))
def invoice_pdf(request, payment_id):
    payment = get_downloadable_payment(request.api_user, payment_id)
    if payment is None:
        return error(404, 'not_found', 'Invoice tidak ditemukan atau pembayaran belum disetujui.')
    return invoice_response(payment)


@api(['DELETE'], auth='required', rate=(60, 60))
def inbox_delete(request, msg_id):
    # filtered by user -> a user can only ever delete their own messages
    inboxMessage.objects.filter(id=msg_id, user=request.api_user).delete()
    return JsonResponse({'ok': True})


def _get_book(book_id):
    uid = _uuid_or_none(book_id)
    return Books.objects.filter(id=uid).first() if uid else None


@api(['POST', 'DELETE'], auth='required', rate=(60, 60))
def wishlist(request, book_id):
    book, user = _get_book(book_id), request.api_user
    if book is None:
        return error(404, 'not_found', 'Buku tidak ditemukan.')
    if request.method == 'DELETE':
        MyWishlist.objects.filter(user=user, book=book).delete()
        return JsonResponse({'in_wishlist': False})
    if UserBook.objects.filter(id_user=user, id_book=book).exists():
        return error(409, 'owned', 'Buku sudah ada di koleksi Anda.')
    MyWishlist.objects.get_or_create(user=user, book=book)
    return JsonResponse({'in_wishlist': True})


@api(['POST', 'DELETE'], auth='required', rate=(60, 60))
def cart(request, book_id):
    book, user = _get_book(book_id), request.api_user
    if book is None:
        return error(404, 'not_found', 'Buku tidak ditemukan.')
    if request.method == 'DELETE':
        MyCart.objects.filter(user=user, book=book).delete()
        return JsonResponse({'in_cart': False})
    if book.kategori_id == 3:
        return error(409, 'free_book', 'Buku gratis tidak perlu dibeli.')
    if not book.is_active:
        return error(409, 'inactive', 'Buku ini sedang tidak dijual.')
    if UserBook.objects.filter(id_user=user, id_book=book).exists():
        return error(409, 'owned', 'Buku sudah ada di koleksi Anda.')
    if MyPaymentDetail.objects.filter(payment__user=user, payment__is_verified=False,
                                      payment__is_canceled=False, book=book).exists():
        return error(409, 'pending', 'Pembelian buku ini sedang diverifikasi admin.')
    MyWishlist.objects.filter(user=user, book=book).delete()
    MyCart.objects.get_or_create(user=user, book=book, defaults={'is_checked': False})
    return JsonResponse({'in_cart': True})


# ----------------------------------------------- reader: komentar / penanda / rencana / progres

def _readable_book(user, book_id):
    """Buku yang boleh diberi penanda / komentar: milik user atau buku gratis."""
    book = _get_book(book_id)
    if book is None:
        return None, error(404, 'not_found', 'Buku tidak ditemukan.')
    owned = UserBook.objects.filter(id_user=user, id_book=book).exists()
    if not book.is_active and not owned:  # nonaktif: hanya pemiliknya (sama seperti book_detail)
        return None, error(404, 'not_found', 'Buku tidak ditemukan.')
    if book.kategori_id != 3 and not owned:
        return None, error(403, 'not_owned', 'Fitur ini hanya untuk buku yang sudah dibeli atau buku gratis.')
    return book, None


def _captcha_or_error(request, action):
    if _recaptcha_ok(request.json.get('recaptcha_token'), throttle.client_ip(request), action):
        return None
    return error(400, 'captcha_failed', 'Verifikasi reCAPTCHA gagal, silakan coba lagi.')


def _bookmark_dict(b):
    return {'id': str(b.id), 'page': b.page, 'color': b.color, 'note': b.note,
            'updated_at': b.updated_at.isoformat()}


def _int_in(value, lo, hi):
    if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
        return None
    return value


@api(['POST'], auth='required', rate=(20, 60))
def book_comment_create(request, book_id):
    book, err = _readable_book(request.api_user, book_id)
    if err:
        return err
    text = request.json.get('comment')
    text = text.strip() if isinstance(text, str) else ''
    if not text or len(text) > 1000:
        return error(400, 'invalid_input', 'Komentar wajib diisi (maksimal 1000 karakter).')
    err = _captcha_or_error(request, 'comment')
    if err:
        return err
    if throttle.hit('book-comment', '%s:%s' % (request.api_user.id, book.id), 5, 10 * 60)[0] is False:
        return error(429, 'rate_limited', 'Terlalu banyak komentar, coba lagi nanti.')
    c = BookComment.objects.create(book=book, user=request.api_user, comment=text)
    return JsonResponse({'name': person_name(request.api_user), 'comment': c.comment,
                         'date': c.created_at.isoformat()}, status=201)


@api(['GET', 'POST'], auth='required', rate=(60, 60))
def book_bookmarks(request, book_id):
    user = request.api_user
    book, err = _readable_book(user, book_id)
    if err:
        return err
    if request.method == 'GET':
        rows = ReaderBookmark.objects.filter(user=user, book=book)
        return JsonResponse({'results': [_bookmark_dict(b) for b in rows]})
    page = _int_in(request.json.get('page'), 1, max(book.halaman, 1))
    color = request.json.get('color', 'red')
    note = request.json.get('note', '')
    if page is None or color not in BOOKMARK_COLORS or not isinstance(note, str) or len(note) > 2000:
        return error(400, 'invalid_input', 'Data penanda tidak valid.')
    err = _captcha_or_error(request, 'bookmark')
    if err:
        return err
    b, created = ReaderBookmark.objects.update_or_create(
        user=user, book=book, page=page, defaults={'color': color, 'note': note.strip()})
    return JsonResponse(_bookmark_dict(b), status=201 if created else 200)


@api(['DELETE'], auth='required', rate=(60, 60))
def bookmark_delete(request, bookmark_id):
    uid = _uuid_or_none(bookmark_id)
    n, _ = ReaderBookmark.objects.filter(id=uid, user=request.api_user).delete() if uid else (0, 0)
    if not n:
        return error(404, 'not_found', 'Penanda tidak ditemukan.')
    return JsonResponse({'deleted': True})


def _plan_dict(p):
    return {'start_date': p.start_date.isoformat(), 'target_date': p.target_date.isoformat(),
            'start_page': p.start_page}


@api(['GET', 'PUT', 'DELETE'], auth='required', rate=(60, 60))
def book_plan(request, book_id):
    user = request.api_user
    book, err = _readable_book(user, book_id)
    if err:
        return err
    if request.method == 'DELETE':
        ReadingPlan.objects.filter(user=user, book=book).delete()
        return JsonResponse({'plan': None})
    if request.method == 'PUT':
        try:
            target = datetime.date.fromisoformat(str(request.json.get('target_date')))
        except ValueError:
            return error(400, 'invalid_input', 'Tanggal target tidak valid.')
        today = datetime.date.today()
        if not today <= target <= today + datetime.timedelta(days=365 * 2):
            return error(400, 'invalid_input', 'Tanggal target harus antara hari ini dan 2 tahun ke depan.')
        start_page = _int_in(request.json.get('start_page', 1), 1, max(book.halaman, 1)) or 1
        ReadingPlan.objects.update_or_create(
            user=user, book=book,
            defaults={'start_date': today, 'target_date': target, 'start_page': start_page})
    plan = ReadingPlan.objects.filter(user=user, book=book).first()
    return JsonResponse({'plan': _plan_dict(plan) if plan else None})


@api(['GET', 'PUT'], auth='required', rate=(120, 60))
def book_progress(request, book_id):
    user = request.api_user
    book, err = _readable_book(user, book_id)
    if err:
        return err
    if request.method == 'PUT':
        page = _int_in(request.json.get('page'), 1, max(book.halaman, 1))
        if page is None:
            return error(400, 'invalid_input', 'Halaman tidak valid.')
        ReadingProgress.objects.update_or_create(user=user, book=book, defaults={'page': page})
        UserBook.objects.filter(id_user=user, id_book=book).update(last_page=page)
        return JsonResponse({'page': page})
    page = ReadingProgress.objects.filter(user=user, book=book).values_list('page', flat=True).first()
    return JsonResponse({'page': page or 0})


@api(['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'], rate=(60, 60))
def not_found(request, *args, **kwargs):
    return error(404, 'not_found', 'Endpoint tidak ditemukan.')


# ----------------------------------------------------------------- images

IMG_WIDTHS = (240, 480, 800)
# public, non-personal media folders the app may request resized copies of
IMG_DIRS = ('blogs', 'gambar_instagram', 'gambar_category', 'profile')


def _resized(src, key, width):
    """Resized + cached JPEG (~15-60 KB instead of 0.3-5 MB originals)."""
    from PIL import Image
    if not os.path.isfile(src):
        return None
    dst_dir = os.path.join(settings.MEDIA_ROOT, 'thumbs')
    dst = os.path.join(dst_dir, '%s_%d.jpg' % (key, width))
    if os.path.isfile(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        return dst
    os.makedirs(dst_dir, exist_ok=True)
    with Image.open(src) as im:
        im.draft('RGB', (width * 2, width * 3))  # fast JPEG down-decode
        if im.mode in ('RGBA', 'LA', 'P'):  # PNG with transparency -> white background
            im = im.convert('RGBA')
            bg = Image.new('RGB', im.size, 'white')
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert('RGB')
        im.thumbnail((width, width * 2))
        tmp = dst + '.%s.tmp' % uuid.uuid4().hex
        im.save(tmp, 'JPEG', quality=78, optimize=True, progressive=True)
    os.replace(tmp, dst)  # atomic: concurrent workers never see a half-written file
    return dst


def _image_response(request, path):
    if path is None:
        return error(404, 'not_found', 'Gambar tidak tersedia.')
    st = os.stat(path)
    etag = '"%x-%x"' % (int(st.st_mtime), st.st_size)
    if request.META.get('HTTP_IF_NONE_MATCH') == etag:  # revalidation costs ~0 bytes
        resp = HttpResponse(status=304)
    else:
        resp = FileResponse(open(path, 'rb'), content_type='image/jpeg')
    resp['ETag'] = etag
    return resp


def _width(request):
    try:
        w = int(request.GET.get('w', 480))
    except ValueError:
        w = 480
    return w if w in IMG_WIDTHS else 480  # whitelist: no arbitrary sizes


@api(['GET'], rate=(600, 60), cache_seconds=86400)
def book_cover(request, book_id):
    uid = _uuid_or_none(book_id)
    w = _width(request)
    src = os.path.join(settings.MEDIA_ROOT, 'extract', 'pdf_full', str(uid), '1.jpg') if uid else None
    return _image_response(request, _resized(src, str(uid), w) if src else None)


@api(['GET'], rate=(600, 60), cache_seconds=86400)
def media_image(request):
    """Resized copy of an allow-listed public image: ?p=blogs/x.jpg&w=480"""
    import hashlib
    rel = (request.GET.get('p') or '')[:200]
    root = os.path.realpath(settings.MEDIA_ROOT)
    src = os.path.realpath(os.path.join(root, rel))
    top = rel.replace('\\', '/').split('/', 1)[0]
    # must be inside MEDIA_ROOT/<allowed dir>/ (also defeats ../ and symlink tricks)
    if top not in IMG_DIRS or not src.startswith(os.path.join(root, top) + os.sep):
        return _image_response(request, None)
    key = hashlib.sha256(rel.encode()).hexdigest()[:24]
    return _image_response(request, _resized(src, key, _width(request)))
