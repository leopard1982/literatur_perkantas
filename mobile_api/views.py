import datetime
import os
import uuid

from django.contrib.auth import authenticate
from django.core.cache import cache
from django.core.paginator import EmptyPage, Paginator
from django.db import transaction
from django.db.models import Count, F, Q
from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.gzip import gzip_page

from literatur.models import (
    Blogs, BlogComment, BookComment, Books, Category, FeaturedBook, Instagram,
    MyCart, MyPaymentDetail, inboxMessage, MyWishlist, OnSaleBook, PageReview, Pengumuman,
    UserBook,
)

from . import throttle
from .core import api, error
from .models import ACCESS_TTL, ApiSession, hash_token, password_stamp
from .serializers import (
    active_sale, blog_dict, book_dict, cover, media, person_name, plain_text,
    safe_https,
)

DEFAULT_PENGUMUMAN = "Selamat Datang Di Website Literatur Perkantas Nasional!"
HOME_CACHE_KEY = 'api:home:v1'
HOME_CACHE_TTL = 60
MAX_SESSIONS_PER_USER = 10

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


@gzip_page
@api(['GET'], auth='required', rate=(120, 60))
def collection(request):
    rows = (UserBook.objects.filter(id_user=request.api_user)
            .select_related('id_book__kategori', 'id_book__onsalebook').order_by('-id'))
    return JsonResponse({'results': [dict(book_dict(u.id_book, 0), last_page=u.last_page) for u in rows]})


@api(['GET'], auth='required', rate=(120, 60))
def inbox(request):
    rows = inboxMessage.objects.filter(user=request.api_user).order_by('-id')[:50]
    return JsonResponse({'results': [{'id': m.id, 'header': m.header, 'body': m.body,
                                      'created_at': m.created_at.isoformat()} for m in rows]})


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


@api(['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'], rate=(60, 60))
def not_found(request, *args, **kwargs):
    return error(404, 'not_found', 'Endpoint tidak ditemukan.')


# ----------------------------------------------------------------- images

IMG_WIDTHS = (240, 480, 800)
# public, non-personal media folders the app may request resized copies of
IMG_DIRS = ('blogs', 'gambar_instagram', 'gambar_category')


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
