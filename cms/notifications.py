import datetime

from literatur.models import Blogs, BookReview, MyDonation, MyPayment, PageReview

NOTIFICATION_KIND_ROLES = {
    'payment': {'Keuangan'},
    'donation': {'Keuangan'},
    'coretan_moderation': {'Admin', 'Superadmin'},
    'review_sahabat': {'Admin', 'Superadmin'},
    'review_buku': {'Admin', 'Superadmin'},
    'coretan_status': {'Penulis'},
}


def get_notifications(user, is_super, roles):
    """Build a live notification feed from existing data (no stored Notification rows)."""
    can_keuangan = is_super or 'Keuangan' in roles
    can_moderate = is_super or bool(roles & {'Admin', 'Superadmin'})
    is_penulis = 'Penulis' in roles and not can_moderate and not can_keuangan

    items = []

    if can_keuangan:
        for payment in MyPayment.objects.filter(is_verified=False, is_canceled=False).order_by('-created_at')[:25]:
            items.append({
                'kind': 'payment',
                'title': 'Pembayaran menunggu verifikasi',
                'message': f'Invoice {payment.payment} • Rp {payment.total:,.0f}'.replace(',', '.'),
                'created_at': payment.created_at,
                'urgent': True,
                'url': f'/cms/notifications/payment/{payment.payment}/',
            })
        for donation in MyDonation.objects.filter(is_verified=False, is_canceled=False).order_by('-created_at')[:25]:
            items.append({
                'kind': 'donation',
                'title': 'Donasi menunggu verifikasi',
                'message': f'Dari {donation.initial} • Rp {donation.nilai:,.0f}'.replace(',', '.'),
                'created_at': donation.created_at,
                'urgent': True,
                'url': f'/cms/notifications/donation/{donation.donation}/',
            })

    if can_moderate:
        for blog in Blogs.objects.filter(tipe='Coretan Pena', is_active=False).select_related('author').order_by('-created_at')[:25]:
            items.append({
                'kind': 'coretan_moderation',
                'title': 'Coretan pena menunggu moderasi',
                'message': f'"{blog.header}" oleh {blog.author.username}',
                'created_at': blog.created_at,
                'urgent': True,
                'url': f'/cms/notifications/coretan_moderation/{blog.id}/',
            })
        for review in PageReview.objects.filter(is_active=False).select_related('user').order_by('-created_at')[:25]:
            items.append({
                'kind': 'review_sahabat',
                'title': 'Review sahabat menunggu moderasi',
                'message': f'Dari {review.user.username}',
                'created_at': review.created_at,
                'urgent': True,
                'url': f'/cms/notifications/review_sahabat/{review.id}/',
            })
        for review in BookReview.objects.filter(is_published=False).select_related('id_buku', 'id_customer').order_by('-updated_review')[:25]:
            items.append({
                'kind': 'review_buku',
                'title': 'Review buku menunggu moderasi',
                'message': f'{review.id_buku.judul} oleh {review.id_customer.nama_lengkap}',
                'created_at': datetime.datetime.combine(review.updated_review, datetime.time.min),
                'urgent': True,
                'url': f'/cms/notifications/review_buku/{review.id}/',
            })

    if is_penulis and user is not None:
        posts = Blogs.objects.filter(tipe='Coretan Pena', author=user).order_by('-updated_at')[:25]
        for post in posts:
            items.append({
                'kind': 'coretan_status',
                'title': 'Coretan pena sudah tayang' if post.is_active else 'Menunggu moderasi admin',
                'message': f'"{post.header}"',
                'created_at': post.updated_at,
                'urgent': not post.is_active,
                'url': f'/cms/notifications/coretan_status/{post.id}/',
            })

    items.sort(key=lambda item: item['created_at'], reverse=True)
    return items
