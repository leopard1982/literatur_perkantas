from .notifications import get_notifications
from .roles import ROLE_ACCESS, STRICT_ROLE_MODULES

NAV_CATALOG = [
    {'module': 'payments', 'label': 'Payment', 'href': '/cms/payments/'},
    {'module': 'donations', 'label': 'Donasi', 'href': '/cms/donations/'},
    {'module': 'books', 'label': 'Buku', 'href': '/cms/books/'},
    {'module': 'categories', 'label': 'Kategori', 'href': '/cms/categories/'},
    {'module': 'promo_bestseller', 'label': 'Promo & Best Seller', 'href': '/cms/promo/'},
    {'module': 'customers', 'label': 'Pelanggan', 'href': '/cms/customers/'},
    {'module': 'content_moderation', 'label': 'Moderasi Konten', 'href': '/cms/content/'},
    {'module': 'instagram_settings', 'label': 'Pengaturan Instagram', 'href': '/cms/instagram/'},
    {'module': 'roles', 'label': 'Role & User', 'href': '/cms/roles/'},
    {'module': 'coretan_pena', 'label': 'Coretan Pena', 'href': '/cms/coretan-pena/'},
    {'module': 'activity_log', 'label': 'Log Transaksi', 'href': '/cms/logs/'},
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
