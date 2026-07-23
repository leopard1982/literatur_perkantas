CMS_ROLE_GROUPS = ['Keuangan', 'Admin', 'Superadmin', 'Penulis']
CMS_ROLE_CHOICES = [(role, role) for role in CMS_ROLE_GROUPS]

ROLE_ACCESS = {
    'payments': {'Keuangan', 'Admin', 'Superadmin'},
    'donations': {'Keuangan', 'Admin', 'Superadmin'},
    'books': {'Admin', 'Superadmin'},
    'categories': {'Admin', 'Superadmin'},
    'promo_bestseller': {'Admin', 'Superadmin'},
    'customers': {'Admin', 'Superadmin'},
    'content_moderation': {'Admin', 'Superadmin'},
    'instagram_settings': {'Admin', 'Superadmin'},
    'roles': {'Superadmin'},
    'activity_log': {'Superadmin'},
    'coretan_pena': {'Penulis'},
}

# Modules where authorship/identity is what grants access, not permission tier —
# even a Django superuser must actually hold the role to use them.
STRICT_ROLE_MODULES = {'coretan_pena'}

ROLE_LABELS = {
    'Keuangan': 'Keuangan',
    'Admin': 'Admin',
    'Superadmin': 'Superadmin',
    'Penulis': 'Penulis',
}
