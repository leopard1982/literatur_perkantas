from django.urls import reverse

from .models import inboxMessage


PUBLIC_BREADCRUMB_LABELS = {
    'main_page': 'Beranda',
    'baca_buku': 'Baca Buku',
    'baca_buku_koleksi': 'Baca Koleksi',
    'semua_buku_koleksi': 'Koleksiku',
    'sinopsis_buku': 'Detail Buku',
    'reset_password': 'Lupa Password',
    'verify_link_lupa_password': 'Verifikasi Password',
    'all_book_view': 'Semua Buku',
    'cart_view': 'Keranjang',
    'list_inbox_message': 'Inbox',
    'all_blogs_view': 'Coretan Pena',
    'detail_blog': 'Detail Blog',
    'payment_process': 'Pembayaran',
    'profile_view': 'Profil',
    'ganti_password_page': 'Ganti Password',
    'profile_update': 'Ubah Profil',
    'list_payment': 'Pembelian',
    'pencarian_info': 'Pencarian',
    'tentang_kami': 'Tentang Kami',
    'melakukan_donasi': 'Donasi',
}

PUBLIC_BREADCRUMB_PARENTS = {
    'baca_buku_koleksi': ['semua_buku_koleksi'],
    'sinopsis_buku': ['all_book_view'],
    'detail_blog': ['all_blogs_view'],
    'payment_process': ['cart_view'],
    'ganti_password_page': ['profile_view'],
    'profile_update': ['profile_view'],
    'list_payment': ['profile_view'],
}

CMS_BREADCRUMB_LABELS = {
    'cms_dashboard': 'Dashboard CMS',
    'cms_login': 'Login CMS',
    'cms_books_dashboard': 'Management Buku',
    'cms_pricing_dashboard': 'Management Harga',
    'cms_payment_dashboard': 'Management Payment',
    'cms_users_dashboard': 'Management Pengguna',
    'cms_donations_dashboard': 'Management Donasi',
    'cms_content_dashboard': 'Management Konten',
    'cms_reports_dashboard': 'Laporan & Audit',
}

CMS_BREADCRUMB_PARENTS = {
    'cms_books_dashboard': ['cms_dashboard'],
    'cms_pricing_dashboard': ['cms_dashboard'],
    'cms_payment_dashboard': ['cms_dashboard'],
    'cms_users_dashboard': ['cms_dashboard'],
    'cms_donations_dashboard': ['cms_dashboard'],
    'cms_content_dashboard': ['cms_dashboard'],
    'cms_reports_dashboard': ['cms_dashboard'],
}


def _build_crumbs(home_label, home_url, url_name, labels, parents):
    crumbs = [{'label': home_label, 'url': home_url, 'active': url_name == home_url}]

    if not url_name:
        crumbs[0]['active'] = True
        return crumbs

    parent_names = parents.get(url_name, [])

    for parent_name in parent_names:
        label = labels.get(parent_name)
        if not label:
            continue
        crumbs.append({
            'label': label,
            'url': reverse(parent_name),
            'active': False,
        })

    current_label = labels.get(url_name)
    if current_label and current_label != home_label:
        crumbs.append({
            'label': current_label,
            'url': '',
            'active': True,
        })
    else:
        crumbs[-1]['active'] = True

    return crumbs


def breadcrumbs(request):
    resolver_match = getattr(request, 'resolver_match', None)
    url_name = resolver_match.url_name if resolver_match else ''

    if request.path.startswith('/cms/'):
        home_url = reverse('cms_dashboard')
        return {
            'breadcrumbs': _build_crumbs(
                'Dashboard CMS',
                home_url,
                url_name,
                CMS_BREADCRUMB_LABELS,
                CMS_BREADCRUMB_PARENTS,
            )
        }

    home_url = reverse('main_page')
    return {
        'breadcrumbs': _build_crumbs(
            'Beranda',
            home_url,
            url_name,
            PUBLIC_BREADCRUMB_LABELS,
            PUBLIC_BREADCRUMB_PARENTS,
        )
    }


def nav_notifications(request):
    if not request.user.is_authenticated:
        return {
            'nav_inbox_message': [],
            'nav_jml_inbox_message': 0,
        }

    notice_qs = inboxMessage.objects.filter(user=request.user).order_by('-id')
    return {
        'nav_inbox_message': notice_qs[:10],
        'nav_jml_inbox_message': notice_qs.count(),
    }
