import datetime
import html
from urllib.parse import quote

from django.utils.html import strip_tags

MEDIA_PREFIX = '/media/'


def media(name):
    # Relative URLs only: the app resolves them against its own configured base
    # URL, so a spoofed Host header can never poison cached responses.
    # Served through the resizing endpoint so phones never download originals.
    return ('/api/v1/img/?p=' + quote(str(name).lstrip('/'))) if name else None


def cover(book_id):
    # resized + cached by the API (see views.book_cover), not the raw 2500px scan
    return '/api/v1/books/%s/cover/' % book_id


def plain_text(value):
    return html.unescape(strip_tags(value or '')).strip()


def active_sale(book):
    sale = getattr(book, 'onsalebook', None)
    if sale and sale.is_active and sale.end_date >= datetime.date.today():
        return sale
    return None


def book_dict(b, bought=None):
    sale = active_sale(b)
    if bought is None:
        bought = getattr(b, 'jumlah_dibeli', 0) or 0
    return {
        'id': str(b.id),
        'judul': b.judul,
        'pengarang': b.pengarang,
        'halaman': b.halaman,
        'price': int(b.price),
        'nett_price': int(sale.nett_price) if sale else None,
        'discount': float(sale.discount) if sale else None,
        'is_free': b.kategori_id == 3,
        'is_best_seller': bool(b.is_best_seller),
        'is_active': bool(b.is_active),  # False = readable but not purchasable
        'jumlah_dibeli': bought,
        'cover': cover(b.id),
        'kategori': b.kategori.nama if b.kategori_id else '',
    }


def person_name(user):
    """Public display name. Never the username/email (may be PII)."""
    d = getattr(user, 'userdetail', None)
    name = (d.alias or d.nama_lengkap) if d else ''
    return (name or 'Sahabat Litanas')[:60]


def blog_dict(b, full=False):
    text = plain_text(b.body)
    d = {
        'id': str(b.id),
        'tipe': b.tipe,
        'header': b.header,
        'excerpt': text[:120] + ('…' if len(text) > 120 else ''),
        'image': media(b.image.name) if b.image else None,
        'author': person_name(b.author),
        'created_at': b.created_at.isoformat(),
    }
    if full:
        d['body'] = text
    return d


def safe_https(url):
    url = (url or '').strip()
    return url if url.lower().startswith('https://') and len(url) <= 300 else None
