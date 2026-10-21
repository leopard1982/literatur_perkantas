from .notifications import get_notifications
from .roles import ROLE_ACCESS, STRICT_ROLE_MODULES

NAV_CATALOG = [
    {'module': 'analytics', 'label': 'Analitik', 'href': '/cms/analytics/', 'icon': 'bi-bar-chart-line'},
    {'module': 'payments', 'label': 'Payment', 'href': '/cms/payments/', 'icon': 'bi-credit-card'},
    {'module': 'donations', 'label': 'Donasi', 'href': '/cms/donations/', 'icon': 'bi-heart'},
    {'module': 'books', 'label': 'Buku', 'href': '/cms/books/', 'icon': 'bi-book'},
    {'module': 'categories', 'label': 'Kategori', 'href': '/cms/categories/', 'icon': 'bi-grid'},
    {'module': 'promo_bestseller', 'label': 'Promo & Best Seller', 'href': '/cms/promo/', 'icon': 'bi-star'},
    {'module': 'customers', 'label': 'Pelanggan', 'href': '/cms/customers/', 'icon': 'bi-people'},
    {'module': 'content_moderation', 'label': 'Moderasi Konten', 'href': '/cms/content/', 'icon': 'bi-shield-check'},
    {'module': 'instagram_settings', 'label': 'Instagram', 'href': '/cms/instagram/', 'icon': 'bi-instagram'},
    {'module': 'pengumuman_settings', 'label': 'Pengumuman', 'href': '/cms/pengumuman/', 'icon': 'bi-megaphone'},
    {'module': 'roles', 'label': 'Role & User', 'href': '/cms/roles/', 'icon': 'bi-person-lock'},
    {'module': 'coretan_pena', 'label': 'Coretan Pena', 'href': '/cms/coretan-pena/', 'icon': 'bi-pencil-square'},
    {'module': 'activity_log', 'label': 'Log Transaksi', 'href': '/cms/logs/', 'icon': 'bi-activity'},
]


def cms_nav(request):
    if not request.path.startswith('/cms/'):
        return {}

    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}

    is_super = user.is_superuser
    roles = set(user.groups.values_list('name', flat=True))

    links = []
    for entry in NAV_CATALOG:
        module = entry['module']
        has_access = (
            bool(roles & ROLE_ACCESS.get(module, set()))
            if module in STRICT_ROLE_MODULES
            else is_super or bool(roles & ROLE_ACCESS.get(module, set()))
        )
        if has_access:
            links.append({
                'label': entry['label'],
                'icon': entry['icon'],
                'href': entry['href'],
                'active': request.path.startswith(entry['href']),
            })

    notifications = get_notifications(user, is_super, roles)

    return {
        'cms_nav_links': links,
        'cms_dashboard_active': request.path == '/cms/',
        'cms_bell_notifications': notifications[:8],
        'cms_bell_count': len([item for item in notifications if item['urgent']]),
    }
