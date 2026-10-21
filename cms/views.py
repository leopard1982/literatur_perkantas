import datetime
import io
import os
import shutil
import uuid

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, ProtectedError, Q, RestrictedError, Sum
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from literatur.models import (
    BlogPost, BlogPostImage, Blogs, BookComment, Books, QrisCode, ensure_default_qris, Category, CmsActivityLog, Instagram, MyDonation, MyPayment,
    MobileBroadcast, MyPaymentDetail, OnSaleBook, PageReview, Pengumuman, SiteVisit, UserBook, UserDetail,
)
from literatur.forms import FormCmsLoginRecaptcha
from literatur.views import get_pengumuman_text
from literatur.pdf_jobs import read_progress, start_pdf_conversion

from .forms import (
    QrisUploadForm,
    BlogPostForm, BookForm, CategoryQuickForm, CmsUserCreateForm, CoretanPenaForm, InstagramForm, MobileBroadcastForm, OnSaleForm,
    PengumumanForm,
)
from .notifications import NOTIFICATION_KIND_ROLES, get_notifications
from .roles import CMS_ROLE_CHOICES, CMS_ROLE_GROUPS, ROLE_ACCESS, STRICT_ROLE_MODULES


CARD_CATALOG = [
    {
        'module': 'analytics',
        'title': 'Analitik',
        'subtitle': 'Pengunjung web & mobile, pembelian, buku, coretan pena, dan donasi.',
        'href': '/cms/analytics/',
        'count_label': 'Pengunjung Hari Ini',
        'tone': 'navy',
    },
    {
        'module': 'payments',
        'title': 'Management Payment',
        'subtitle': 'Verifikasi pembayaran, antrean invoice, dan tindak lanjut approval.',
        'href': '/cms/payments/',
        'count_label': 'Pending',
        'tone': 'clay',
    },
    {
        'module': 'donations',
        'title': 'Management Donasi',
        'subtitle': 'Validasi bukti donasi, status verifikasi, dan monitoring donatur.',
        'href': '/cms/donations/',
        'count_label': 'Pending',
        'tone': 'plum',
    },
    {
        'module': 'books',
        'title': 'Management Buku',
        'subtitle': 'Data master buku, kategori, metadata, dan file PDF buku.',
        'href': '/cms/books/',
        'count_label': 'Total Buku',
        'tone': 'earth',
    },
    {
        'module': 'promo_bestseller',
        'title': 'Promo & Best Seller',
        'subtitle': 'Atur harga promo aktif dan kurasi buku best seller.',
        'href': '/cms/promo/',
        'count_label': 'Promo Aktif',
        'tone': 'amber',
    },
    {
        'module': 'customers',
        'title': 'Management Pelanggan',
        'subtitle': 'Profil pelanggan dan status aktif akun.',
        'href': '/cms/customers/',
        'count_label': 'Total Pelanggan',
        'tone': 'forest',
    },
    {
        'module': 'content_moderation',
        'title': 'Moderasi Konten',
        'subtitle': 'Moderasi coretan pena, review sahabat, dan review buku.',
        'href': '/cms/content/',
        'count_label': 'Menunggu Moderasi',
        'tone': 'navy',
    },
    {
        'module': 'instagram_settings',
        'title': 'Pengaturan Instagram',
        'subtitle': 'Kelola foto dan link feed Instagram yang tampil di halaman utama.',
        'href': '/cms/instagram/',
        'count_label': 'Total Foto',
        'tone': 'plum',
    },
    {
        'module': 'pengumuman_settings',
        'title': 'Pengaturan Pengumuman',
        'subtitle': 'Atur teks pengumuman berjalan yang tampil di halaman utama.',
        'href': '/cms/pengumuman/',
        'count_label': 'Status',
        'tone': 'teal',
    },
    {
        'module': 'roles',
        'title': 'Role & User CMS',
        'subtitle': 'Buat akun staff CMS dan atur peran akses.',
        'href': '/cms/roles/',
        'count_label': 'Akun Staff',
        'tone': 'gold',
    },
    {
        'module': 'blog_posts',
        'title': 'Management Blogs',
        'subtitle': 'Tulis blog dengan banyak foto, arsipkan, dan pantau jumlah dilihat.',
        'href': '/cms/blogs/',
        'count_label': 'Total Blog',
        'tone': 'forest',
    },
    {
        'module': 'coretan_pena',
        'title': 'Coretan Pena',
        'subtitle': 'Tulis dan kelola coretan pena milik Anda sendiri.',
        'href': '/cms/coretan-pena/',
        'count_label': 'Tulisan Saya',
        'tone': 'teal',
    },
]


MONTH_CHOICES = [
    (1, 'Januari'), (2, 'Februari'), (3, 'Maret'), (4, 'April'),
    (5, 'Mei'), (6, 'Juni'), (7, 'Juli'), (8, 'Agustus'),
    (9, 'September'), (10, 'Oktober'), (11, 'November'), (12, 'Desember'),
]


def _report_period(request):
    now = timezone.now()
    try:
        month = int(request.GET.get('month', now.month))
    except (TypeError, ValueError):
        month = now.month
    try:
        year = int(request.GET.get('year', now.year))
    except (TypeError, ValueError):
        year = now.year
    if month < 1 or month > 12:
        month = now.month
    return month, year


def _xlsx_response(filename, header, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    for column_cells in sheet.columns:
        column_letter = column_cells[0].column_letter
        longest = max((len(str(cell.value)) for cell in column_cells if cell.value is not None), default=8)
        sheet.column_dimensions[column_letter].width = min(longest + 2, 40)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    workbook.save(response)
    return response


def _year_choices():
    current_year = timezone.now().year
    return list(range(current_year, current_year - 5, -1))


def _signature_table(available_width):
    signature_table = Table(
        [
            ['Dibuat Oleh,', 'Disetujui Oleh,'],
            ['', ''],
            ['', ''],
            ['', ''],
            ['_____________________', '_____________________'],
            ['Bendahara', ''],
        ],
        colWidths=[available_width / 2, available_width / 2],
    )
    signature_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    return signature_table


def _build_report_pdf(filename, title, period_label, summary_rows, table_header, table_rows, col_ratios=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
    )
    styles = getSampleStyleSheet()
    cell_style = styles['Normal'].clone('cell')
    cell_style.fontSize = 8
    cell_style.leading = 10
    header_style = cell_style.clone('cell-header')
    header_style.textColor = colors.white
    header_style.fontName = 'Helvetica-Bold'

    elements = [
        Paragraph(title, styles['Title']),
        Paragraph(period_label, styles['Normal']),
        Spacer(1, 0.5 * cm),
    ]

    summary_table = Table(summary_rows, hAlign='LEFT', colWidths=[6 * cm, 6 * cm])
    summary_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.7 * cm))

    col_count = len(table_header)
    available_width = A4[0] - 3.2 * cm
    if col_ratios and len(col_ratios) == col_count:
        ratio_sum = sum(col_ratios)
        col_widths = [available_width * ratio / ratio_sum for ratio in col_ratios]
    else:
        col_widths = [available_width / col_count] * col_count

    data = [[Paragraph(str(cell), header_style) for cell in table_header]]
    for row in table_rows:
        data.append([Paragraph(str(cell), cell_style) for cell in row])

    transaction_table = Table(data, colWidths=col_widths, repeatRows=1)
    transaction_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#bf5b3d')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d3c1ac')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5efe6')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(transaction_table)
    elements.append(Spacer(1, 1.5 * cm))

    elements.append(_signature_table(available_width))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _build_receipt_pdf(filename, title, fields):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()

    elements = [
        Paragraph(title, styles['Title']),
        Spacer(1, 0.8 * cm),
    ]

    available_width = A4[0] - 4 * cm
    field_table = Table(fields, colWidths=[available_width * 0.35, available_width * 0.65])
    field_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d3c1ac')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(field_table)
    elements.append(Spacer(1, 1.5 * cm))

    elements.append(_signature_table(available_width))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _breadcrumbs(*items):
    crumbs = []
    total = len(items)
    for index, (label, url) in enumerate(items):
        is_last = index == total - 1
        crumbs.append({'label': label, 'url': None if is_last else url, 'active': is_last})
    return crumbs


def _user_cms_roles(user):
    if not user.is_authenticated:
        return set()
    return set(user.groups.values_list('name', flat=True)) & set(CMS_ROLE_GROUPS)


def _client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _log_activity(request, module, action):
    CmsActivityLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        module=module,
        action=action,
        ip_address=_client_ip(request),
    )


def _can_process_finance(request):
    return 'Keuangan' in _user_cms_roles(request.user)


def _ensure_cms_access(request, module=None):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(f"/cms/login/?next={request.path}")

    roles = _user_cms_roles(request.user)

    if module in STRICT_ROLE_MODULES:
        if not (roles & ROLE_ACCESS.get(module, set())):
            messages.add_message(request, messages.SUCCESS, 'Menulis coretan pena hanya untuk akun dengan peran Penulis.')
            return HttpResponseRedirect('/cms/')
        return None

    if request.user.is_superuser:
        return None

    if not roles:
        messages.add_message(request, messages.SUCCESS, 'Area CMS hanya dapat diakses oleh akun staff Literatur Perkantas.')
        return HttpResponseRedirect('/')

    if module and not (roles & ROLE_ACCESS.get(module, set())):
        messages.add_message(request, messages.SUCCESS, 'Akun Anda tidak memiliki akses ke modul ini.')
        return HttpResponseRedirect('/cms/')

    return None


def login_view(request):
    if request.user.is_authenticated and (request.user.is_superuser or _user_cms_roles(request.user)):
        return HttpResponseRedirect('/cms/')

    next_url = request.GET.get('next') or request.POST.get('next') or '/cms/'

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not FormCmsLoginRecaptcha(request.POST).is_valid():
            messages.add_message(request, messages.SUCCESS, 'Verifikasi keamanan (reCAPTCHA) gagal, silakan coba lagi.')
            user = False
        else:
            user = authenticate(request, username=username, password=password)

        if user is False:
            pass
        elif user is None:
            messages.add_message(request, messages.SUCCESS, 'Username atau password CMS tidak sesuai.')
        elif not (user.is_superuser or _user_cms_roles(user)):
            messages.add_message(request, messages.SUCCESS, 'Akun ditemukan, tetapi tidak memiliki akses staff ke CMS.')
        else:
            login(request, user)
            return HttpResponseRedirect(next_url)

    context = {
        'next_url': next_url,
    }
    return render(request, 'cms/login.html', context)


def logout_view(request):
    logout(request)
    messages.add_message(request, messages.SUCCESS, 'Anda sudah keluar dari CMS.')
    return HttpResponseRedirect('/cms/login/')


def dashboard(request):
    blocked = _ensure_cms_access(request)
    if blocked:
        return blocked

    is_super = request.user.is_superuser
    roles = _user_cms_roles(request.user)

    def has_access(module):
        if module in STRICT_ROLE_MODULES:
            return bool(roles & ROLE_ACCESS.get(module, set()))
        return is_super or bool(roles & ROLE_ACCESS.get(module, set()))

    cards = []
    for card in CARD_CATALOG:
        if not has_access(card['module']):
            continue

        entry = dict(card)
        module = card['module']

        if module == 'analytics':
            entry['count_value'] = SiteVisit.objects.filter(date=datetime.date.today()).count()
        elif module == 'payments':
            entry['count_value'] = MyPayment.objects.filter(is_verified=False, is_canceled=False).count()
        elif module == 'donations':
            entry['count_value'] = MyDonation.objects.filter(is_verified=False, is_canceled=False).count()
        elif module == 'books':
            entry['count_value'] = Books.objects.count()
        elif module == 'promo_bestseller':
            entry['count_value'] = OnSaleBook.objects.filter(is_active=True).count()
        elif module == 'customers':
            entry['count_value'] = User.objects.filter(is_superuser=False, groups__isnull=True).count()
        elif module == 'content_moderation':
            entry['count_value'] = (
                Blogs.objects.filter(tipe='Coretan Pena', is_active=False).count()
                + PageReview.objects.filter(is_active=False).count()
                + BookComment.objects.filter(is_publish=False).count()
            )
        elif module == 'instagram_settings':
            entry['count_value'] = Instagram.objects.count()
        elif module == 'pengumuman_settings':
            entry['count_value'] = 'Aktif' if Pengumuman.objects.exists() else 'Default'
        elif module == 'roles':
            entry['count_value'] = User.objects.filter(groups__name__in=CMS_ROLE_GROUPS).distinct().count()
        elif module == 'blog_posts':
            entry['count_value'] = BlogPost.objects.count()
        elif module == 'coretan_pena':
            entry['count_value'] = Blogs.objects.filter(tipe='Coretan Pena', author=request.user).count()

        cards.append(entry)

    if is_super:
        cards.append({
            'module': 'reports',
            'title': 'Laporan & Audit',
            'subtitle': 'Ringkasan transaksi, log pemroses, dan area audit operasional.',
            'href': '/cms/reports/',
            'count_label': 'Modul',
            'count_value': 'Laporan',
            'tone': 'charcoal',
        })

    summary_tiles = []
    if has_access('payments'):
        summary_tiles.append({'tone': 'warning', 'icon': 'bi-hourglass-split', 'href': '/cms/payments/', 'label': 'Payment Pending', 'value': MyPayment.objects.filter(is_verified=False, is_canceled=False).count()})
        summary_tiles.append({'tone': 'success', 'icon': 'bi-check-circle', 'href': '/cms/payments/', 'label': 'Payment Disetujui', 'value': MyPayment.objects.filter(is_verified=True).count()})
        summary_tiles.append({'tone': 'danger', 'icon': 'bi-x-circle', 'href': '/cms/payments/', 'label': 'Payment Ditolak', 'value': MyPayment.objects.filter(is_verified=False, is_canceled=True).count()})
    if has_access('donations'):
        summary_tiles.append({'tone': 'primary', 'href': '/cms/donations/', 'icon': 'bi-hourglass-split', 'label': 'Donasi Pending', 'value': MyDonation.objects.filter(is_verified=False, is_canceled=False).count()})
        summary_tiles.append({'tone': 'info', 'href': '/cms/donations/', 'icon': 'bi-heart-fill', 'label': 'Donasi Disetujui', 'value': MyDonation.objects.filter(is_verified=True).count()})
        summary_tiles.append({'tone': 'dark', 'href': '/cms/donations/', 'icon': 'bi-x-circle', 'label': 'Donasi Ditolak', 'value': MyDonation.objects.filter(is_verified=False, is_canceled=True).count()})

    card_icons = {
        'analytics': 'bi-bar-chart-line', 'payments': 'bi-credit-card', 'donations': 'bi-heart',
        'books': 'bi-book', 'categories': 'bi-grid', 'promo_bestseller': 'bi-star',
        'customers': 'bi-people', 'content_moderation': 'bi-shield-check',
        'instagram_settings': 'bi-instagram', 'pengumuman_settings': 'bi-megaphone',
        'roles': 'bi-person-lock', 'blog_posts': 'bi-newspaper', 'coretan_pena': 'bi-pencil-square', 'reports': 'bi-clipboard-data',
    }
    tone_bg = {
        'earth': 'secondary', 'amber': 'warning', 'clay': 'danger', 'forest': 'success',
        'plum': 'primary', 'navy': 'primary', 'charcoal': 'dark', 'gold': 'warning', 'teal': 'info',
    }
    for entry in cards:
        entry['icon'] = card_icons.get(entry['module'], 'bi-app')
        entry['bg'] = tone_bg.get(entry['tone'], 'secondary')

    trend = None
    recent_payments = []
    recent_donations = []
    if has_access('payments'):
        days = 14
        start = datetime.date.today() - datetime.timedelta(days=days - 1)
        start_dt = datetime.datetime.combine(start, datetime.time.min)
        rows = [
            {'day': r['created_at__date'], 'total': r['n']}
            for r in MyPayment.objects.filter(is_verified=True, is_canceled=False, created_at__gte=start_dt)
            .values('created_at__date').annotate(n=Sum('total'))
        ]
        labels, values = _daily_series(rows, start, days)
        trend = {'labels': labels, 'values': values, 'days': days}
        recent_payments = list(
            MyPayment.objects.filter(is_verified=False, is_canceled=False)
            .select_related('user').order_by('-created_at')[:5]
        )
    if has_access('donations'):
        recent_donations = list(
            MyDonation.objects.filter(is_verified=False, is_canceled=False).order_by('-created_at')[:5]
        )

    context = {
        'cards': cards,
        'summary_tiles': summary_tiles,
        'roles': ['Superuser'] if is_super else sorted(roles),
        'trend': trend,
        'recent_payments': recent_payments,
        'recent_donations': recent_donations,
        'today': datetime.date.today(),
    }
    return render(request, 'cms/dashboard.html', context)


def module_placeholder(request, title, description, bullets):
    blocked = _ensure_cms_access(request, 'reports')
    if blocked:
        return blocked

    context = {
        'title': title,
        'description': description,
        'bullets': bullets,
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), (title, None)),
    }
    return render(request, 'cms/module_placeholder.html', context)


def _daily_series(rows, start, days, value_key='total'):
    by_day = {row['day']: row[value_key] for row in rows}
    labels, values = [], []
    for offset in range(days):
        day = start + datetime.timedelta(days=offset)
        labels.append(day.strftime('%d %b'))
        values.append(float(by_day.get(day) or 0))
    return labels, values


def analytics_dashboard(request):
    blocked = _ensure_cms_access(request, 'analytics')
    if blocked:
        return blocked

    try:
        days = int(request.GET.get('days', 30))
    except (TypeError, ValueError):
        days = 30
    if days not in (7, 30, 90, 365):
        days = 30

    today = datetime.date.today()
    start = today - datetime.timedelta(days=days - 1)
    start_dt = datetime.datetime.combine(start, datetime.time.min)

    def visits(source):
        qs = SiteVisit.objects.filter(source=source, date__gte=start)
        rows = qs.values('date').annotate(total=Count('id')).values('date', 'total')
        rows = [{'day': r['date'], 'total': r['total']} for r in rows]
        labels, values = _daily_series(rows, start, days)
        return {
            'labels': labels,
            'values': values,
            'unique': qs.values('visitor_key').distinct().count(),
            'hits': qs.aggregate(t=Sum('hits'))['t'] or 0,
        }

    paid = MyPayment.objects.filter(is_verified=True, is_canceled=False, created_at__gte=start_dt)
    pay_rows = [
        {'day': r['created_at__date'], 'total': r['n']}
        for r in paid.values('created_at__date').annotate(n=Count('payment'))
    ]
    pay_labels, pay_values = _daily_series(pay_rows, start, days)
    purchases = {
        'labels': pay_labels,
        'values': pay_values,
        'count': paid.count(),
        'revenue': paid.aggregate(t=Sum('total'))['t'] or 0,
        'books': paid.aggregate(t=Sum('jumlah_buku'))['t'] or 0,
    }

    sold = (
        MyPaymentDetail.objects
        .filter(payment__is_verified=True, payment__is_canceled=False, payment__created_at__gte=start_dt)
        .values('book').annotate(n=Count('id'))
    )
    sold_map = {row['book']: row['n'] for row in sold}
    book_rows = [
        {'judul': b.judul, 'pengarang': b.pengarang, 'sold': sold_map.get(b.id, 0)}
        for b in Books.objects.filter(is_active=True).only('id', 'judul', 'pengarang')
    ]
    top_books = sorted((b for b in book_rows if b['sold'] > 0), key=lambda b: -b['sold'])[:10]
    least_books = sorted(book_rows, key=lambda b: (b['sold'], b['judul']))[:10]

    coretan = Blogs.objects.filter(tipe='Coretan Pena', is_active=True).select_related('author')
    top_coretan = list(coretan.order_by('-view', '-created_at')[:10])
    least_coretan = list(coretan.order_by('view', 'created_at')[:10])

    donations = MyDonation.objects.filter(is_verified=True, is_canceled=False, created_at__gte=start_dt)
    don_rows = [
        {'day': r['created_at__date'], 'total': r['n']}
        for r in donations.values('created_at__date').annotate(n=Sum('nilai'))
    ]
    don_labels, don_values = _daily_series(don_rows, start, days)
    donation_data = {
        'labels': don_labels,
        'values': don_values,
        'count': donations.count(),
        'total': donations.aggregate(t=Sum('nilai'))['t'] or 0,
    }

    tab = request.GET.get('tab', 'pengunjung')
    if tab not in ('pengunjung', 'pembelian', 'buku', 'coretan', 'donasi'):
        tab = 'pengunjung'

    context = {
        'days': days,
        'tab': tab,
        'start': start,
        'today': today,
        'recent_visits': SiteVisit.objects.filter(date__gte=start).order_by('-last_seen')[:200],
        'web': visits('web'),
        'mobile': visits('mobile'),
        'purchases': purchases,
        'top_books': top_books,
        'least_books': least_books,
        'top_coretan': top_coretan,
        'least_coretan': least_coretan,
        'donation': donation_data,
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Analitik', None)),
    }
    return render(request, 'cms/analytics_dashboard.html', context)


def reports_dashboard(request):
    return module_placeholder(
        request,
        'Laporan & Audit',
        'Area ini disiapkan untuk rangkuman operasional dan audit sederhana untuk transaksi dan konten.',
        [
            'Lihat ringkasan pembayaran disetujui, ditolak, dan menunggu.',
            'Pantau invoice yang melewati SLA verifikasi.',
            'Bangun audit trail untuk siapa memproses transaksi dan kapan dilakukan.',
        ],
    )


def payment_dashboard(request):
    blocked = _ensure_cms_access(request, 'payments')
    if blocked:
        return blocked

    status_filter = request.GET.get('status', 'all').strip() or 'all'
    query = request.GET.get('q', '').strip()

    can_process = _can_process_finance(request)

    if request.method == 'POST':
        payment_id = request.POST.get('payment_id', '').strip()
        decision = request.POST.get('decision', '').strip()

        if not can_process:
            messages.add_message(request, messages.SUCCESS, 'Hanya akun dengan peran Keuangan yang dapat memproses persetujuan pembayaran.')
            return HttpResponseRedirect(f"/cms/payments/?status={status_filter}&q={query}")

        try:
            payment = MyPayment.objects.get(payment=payment_id)

            if payment.is_verified or payment.is_canceled:
                messages.add_message(request, messages.SUCCESS, f'Invoice {payment.payment} sudah memiliki status final.')
            elif decision == 'approve':
                payment.is_verified = True
                payment.is_canceled = False
                payment.pemroses = request.user.username
                payment.save()
                messages.add_message(request, messages.SUCCESS, f'Pembayaran {payment.payment} berhasil disetujui.')
                _log_activity(request, 'payments', f'Menyetujui pembayaran {payment.payment}.')
            elif decision == 'reject':
                payment.is_verified = False
                payment.is_canceled = True
                payment.pemroses = request.user.username
                payment.save()
                messages.add_message(request, messages.SUCCESS, f'Pembayaran {payment.payment} berhasil ditolak.')
                _log_activity(request, 'payments', f'Menolak pembayaran {payment.payment}.')
        except Exception as ex:
            print(ex)
            messages.add_message(request, messages.SUCCESS, 'Terjadi kendala saat memproses status pembayaran.')

        return HttpResponseRedirect(f"/cms/payments/?status={status_filter}&q={query}")

    payments = MyPayment.objects.select_related('user', 'user__userdetail').order_by('-created_at')

    if status_filter == 'pending':
        payments = payments.filter(is_verified=False, is_canceled=False)
    elif status_filter == 'approved':
        payments = payments.filter(is_verified=True)
    elif status_filter == 'rejected':
        payments = payments.filter(is_verified=False, is_canceled=True)

    if query:
        payments = payments.filter(
            Q(payment__icontains=query)
            | Q(user__username__icontains=query)
            | Q(user__email__icontains=query)
            | Q(user__userdetail__nama_lengkap__icontains=query)
            | Q(user__userdetail__no_whatsapp__icontains=query)
        )

    paginator = Paginator(payments, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    payments_on_page = list(page_obj.object_list)
    details_by_payment = {}
    if payments_on_page:
        detail_qs = MyPaymentDetail.objects.select_related('book').filter(
            payment__in=[p.payment for p in payments_on_page]
        )
        for detail in detail_qs:
            details_by_payment.setdefault(detail.payment_id, []).append(detail)
    for payment in payments_on_page:
        payment.details = details_by_payment.get(payment.payment, [])

    now = timezone.now()
    stats = {
        'pending': MyPayment.objects.filter(is_verified=False, is_canceled=False).count(),
        'approved': MyPayment.objects.filter(is_verified=True).count(),
        'rejected': MyPayment.objects.filter(is_verified=False, is_canceled=True).count(),
        'overdue': MyPayment.objects.filter(
            is_verified=False,
            is_canceled=False,
            created_at__lt=now - datetime.timedelta(hours=24),
        ).count(),
    }

    report_month, report_year = _report_period(request)
    period_payments = MyPayment.objects.filter(created_at__year=report_year, created_at__month=report_month)
    report = {
        'total_count': period_payments.count(),
        'approved_count': period_payments.filter(is_verified=True).count(),
        'approved_amount': period_payments.filter(is_verified=True).aggregate(total=Sum('total'))['total'] or 0,
        'rejected_count': period_payments.filter(is_verified=False, is_canceled=True).count(),
        'pending_count': period_payments.filter(is_verified=False, is_canceled=False).count(),
    }
    period_transactions = period_payments.select_related('user', 'user__userdetail').order_by('created_at')

    context = {
        'page_obj': page_obj,
        'current_status': status_filter,
        'current_query': query,
        'stats': stats,
        'can_process': can_process,
        'report_month': report_month,
        'report_year': report_year,
        'report': report,
        'period_transactions': period_transactions,
        'month_choices': MONTH_CHOICES,
        'year_choices': _year_choices(),
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Management Payment', None)),
    }
    return render(request, 'cms/payment_dashboard.html', context)


def donation_dashboard(request):
    blocked = _ensure_cms_access(request, 'donations')
    if blocked:
        return blocked

    status_filter = request.GET.get('status', 'all').strip() or 'all'
    query = request.GET.get('q', '').strip()

    can_process = _can_process_finance(request)

    if request.method == 'POST':
        donation_id = request.POST.get('donation_id', '').strip()
        decision = request.POST.get('decision', '').strip()

        if not can_process:
            messages.add_message(request, messages.SUCCESS, 'Hanya akun dengan peran Keuangan yang dapat memproses persetujuan donasi.')
            return HttpResponseRedirect(f"/cms/donations/?status={status_filter}&q={query}")

        try:
            donation = MyDonation.objects.get(donation=donation_id)

            if donation.is_verified or donation.is_canceled:
                messages.add_message(request, messages.SUCCESS, f'Donasi dari {donation.initial} sudah memiliki status final.')
            elif decision == 'approve':
                donation.is_verified = True
                donation.is_canceled = False
                donation.pemroses = request.user.username
                donation.save()
                messages.add_message(request, messages.SUCCESS, f'Donasi dari {donation.initial} berhasil disetujui.')
                _log_activity(request, 'donations', f'Menyetujui donasi dari {donation.initial}.')
            elif decision == 'reject':
                donation.is_verified = False
                donation.is_canceled = True
                donation.pemroses = request.user.username
                donation.save()
                messages.add_message(request, messages.SUCCESS, f'Donasi dari {donation.initial} berhasil ditolak.')
                _log_activity(request, 'donations', f'Menolak donasi dari {donation.initial}.')
        except Exception as ex:
            print(ex)
            messages.add_message(request, messages.SUCCESS, 'Terjadi kendala saat memproses status donasi.')

        return HttpResponseRedirect(f"/cms/donations/?status={status_filter}&q={query}")

    donations = MyDonation.objects.order_by('-created_at')

    if status_filter == 'pending':
        donations = donations.filter(is_verified=False, is_canceled=False)
    elif status_filter == 'approved':
        donations = donations.filter(is_verified=True)
    elif status_filter == 'rejected':
        donations = donations.filter(is_verified=False, is_canceled=True)

    if query:
        donations = donations.filter(
            Q(initial__icontains=query)
            | Q(email__icontains=query)
            | Q(keterangan__icontains=query)
        )

    paginator = Paginator(donations, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    now = timezone.now()
    stats = {
        'pending': MyDonation.objects.filter(is_verified=False, is_canceled=False).count(),
        'approved': MyDonation.objects.filter(is_verified=True).count(),
        'rejected': MyDonation.objects.filter(is_verified=False, is_canceled=True).count(),
        'overdue': MyDonation.objects.filter(
            is_verified=False,
            is_canceled=False,
            created_at__lt=now - datetime.timedelta(hours=24),
        ).count(),
    }

    report_month, report_year = _report_period(request)
    period_donations = MyDonation.objects.filter(created_at__year=report_year, created_at__month=report_month)
    report = {
        'total_count': period_donations.count(),
        'approved_count': period_donations.filter(is_verified=True).count(),
        'approved_amount': period_donations.filter(is_verified=True).aggregate(total=Sum('nilai'))['total'] or 0,
        'rejected_count': period_donations.filter(is_verified=False, is_canceled=True).count(),
        'pending_count': period_donations.filter(is_verified=False, is_canceled=False).count(),
    }
    period_transactions = period_donations.order_by('created_at')

    context = {
        'page_obj': page_obj,
        'current_status': status_filter,
        'current_query': query,
        'stats': stats,
        'can_process': can_process,
        'report_month': report_month,
        'report_year': report_year,
        'report': report,
        'period_transactions': period_transactions,
        'month_choices': MONTH_CHOICES,
        'year_choices': _year_choices(),
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Management Donasi', None)),
    }
    return render(request, 'cms/donation_dashboard.html', context)


def payment_export(request):
    blocked = _ensure_cms_access(request, 'reports')
    if blocked:
        return blocked

    month, year = _report_period(request)
    payments = MyPayment.objects.select_related('user', 'user__userdetail').filter(
        created_at__year=year, created_at__month=month
    ).order_by('created_at')

    month_label = dict(MONTH_CHOICES).get(month, month)

    rows = []
    for payment in payments:
        if payment.is_verified:
            status = 'Disetujui'
        elif payment.is_canceled:
            status = 'Ditolak'
        else:
            status = 'Menunggu'
        rows.append([
            payment.payment,
            payment.user.userdetail.nama_lengkap if hasattr(payment.user, 'userdetail') else payment.user.username,
            payment.user.email,
            float(payment.total),
            payment.jumlah_buku,
            status,
            payment.pemroses or '-',
            payment.created_at.strftime('%d-%m-%Y %H:%M'),
        ])

    response = _xlsx_response(
        f'pembayaran-{year}-{month:02d}.xlsx',
        ['Invoice', 'Nama Pembeli', 'Email', 'Total', 'Jumlah Buku', 'Status', 'Diproses Oleh', 'Tanggal Masuk'],
        rows,
    )
    _log_activity(request, 'payments', f'Mengunduh laporan transaksi pembayaran periode {month_label} {year}.')
    return response


def donation_export(request):
    blocked = _ensure_cms_access(request, 'reports')
    if blocked:
        return blocked

    month, year = _report_period(request)
    donations = MyDonation.objects.filter(created_at__year=year, created_at__month=month).order_by('created_at')

    month_label = dict(MONTH_CHOICES).get(month, month)

    rows = []
    for donation in donations:
        if donation.is_verified:
            status = 'Disetujui'
        elif donation.is_canceled:
            status = 'Ditolak'
        else:
            status = 'Menunggu'
        rows.append([
            donation.initial,
            donation.email,
            float(donation.nilai),
            donation.keterangan or '-',
            status,
            donation.pemroses or '-',
            donation.created_at.strftime('%d-%m-%Y %H:%M'),
        ])

    response = _xlsx_response(
        f'donasi-{year}-{month:02d}.xlsx',
        ['Nama Donatur', 'Email', 'Nilai', 'Keterangan', 'Status', 'Diproses Oleh', 'Tanggal Masuk'],
        rows,
    )
    _log_activity(request, 'donations', f'Mengunduh laporan transaksi donasi periode {month_label} {year}.')
    return response


def payment_report_pdf(request):
    blocked = _ensure_cms_access(request, 'reports')
    if blocked:
        return blocked

    month, year = _report_period(request)
    month_label = dict(MONTH_CHOICES).get(month, month)
    payments = MyPayment.objects.select_related('user', 'user__userdetail').filter(
        created_at__year=year, created_at__month=month
    ).order_by('created_at')

    table_rows = []
    for index, payment in enumerate(payments, start=1):
        if payment.is_verified:
            status = 'Disetujui'
        elif payment.is_canceled:
            status = 'Ditolak'
        else:
            status = 'Menunggu'
        table_rows.append([
            str(index),
            payment.payment,
            payment.user.userdetail.nama_lengkap if hasattr(payment.user, 'userdetail') else payment.user.username,
            f'Rp {payment.total:,.0f}',
            status,
            payment.pemroses or '-',
            payment.created_at.strftime('%d-%m-%Y'),
        ])

    approved_amount = payments.filter(is_verified=True).aggregate(total=Sum('total'))['total'] or 0
    summary_rows = [
        ['Total Transaksi', str(payments.count())],
        ['Disetujui', str(payments.filter(is_verified=True).count())],
        ['Ditolak', str(payments.filter(is_verified=False, is_canceled=True).count())],
        ['Menunggu', str(payments.filter(is_verified=False, is_canceled=False).count())],
        ['Total Nilai Disetujui', f'Rp {approved_amount:,.0f}'],
    ]

    response = _build_report_pdf(
        f'laporan-pembayaran-{year}-{month:02d}.pdf',
        'Laporan Transaksi Pembayaran',
        f'Periode: {month_label} {year}',
        summary_rows,
        ['No', 'Invoice', 'Nama Pembeli', 'Total', 'Status', 'Disetujui Oleh', 'Tanggal'],
        table_rows,
        col_ratios=[0.4, 2.2, 1.5, 1, 0.9, 1.2, 1],
    )
    _log_activity(request, 'payments', f'Mengunduh laporan PDF pembayaran periode {month_label} {year}.')
    return response


def donation_report_pdf(request):
    blocked = _ensure_cms_access(request, 'reports')
    if blocked:
        return blocked

    month, year = _report_period(request)
    month_label = dict(MONTH_CHOICES).get(month, month)
    donations = MyDonation.objects.filter(created_at__year=year, created_at__month=month).order_by('created_at')

    table_rows = []
    for index, donation in enumerate(donations, start=1):
        if donation.is_verified:
            status = 'Disetujui'
        elif donation.is_canceled:
            status = 'Ditolak'
        else:
            status = 'Menunggu'
        table_rows.append([
            str(index),
            donation.initial,
            f'Rp {donation.nilai:,.0f}',
            status,
            donation.pemroses or '-',
            donation.created_at.strftime('%d-%m-%Y'),
        ])

    approved_amount = donations.filter(is_verified=True).aggregate(total=Sum('nilai'))['total'] or 0
    summary_rows = [
        ['Total Transaksi', str(donations.count())],
        ['Disetujui', str(donations.filter(is_verified=True).count())],
        ['Ditolak', str(donations.filter(is_verified=False, is_canceled=True).count())],
        ['Menunggu', str(donations.filter(is_verified=False, is_canceled=False).count())],
        ['Total Nilai Disetujui', f'Rp {approved_amount:,.0f}'],
    ]

    response = _build_report_pdf(
        f'laporan-donasi-{year}-{month:02d}.pdf',
        'Laporan Transaksi Donasi',
        f'Periode: {month_label} {year}',
        summary_rows,
        ['No', 'Nama Donatur', 'Nilai', 'Status', 'Disetujui Oleh', 'Tanggal'],
        table_rows,
        col_ratios=[0.4, 1.8, 1.2, 0.9, 1.2, 1],
    )
    _log_activity(request, 'donations', f'Mengunduh laporan PDF donasi periode {month_label} {year}.')
    return response


def payment_receipt_pdf(request, payment_id):
    blocked = _ensure_cms_access(request, 'payments')
    if blocked:
        return blocked

    payment = get_object_or_404(MyPayment, pk=payment_id)
    if payment.is_verified:
        status = 'Disetujui'
    elif payment.is_canceled:
        status = 'Ditolak'
    else:
        status = 'Menunggu'

    fields = [
        ['Invoice', payment.payment],
        ['Nama Pembeli', payment.user.userdetail.nama_lengkap if hasattr(payment.user, 'userdetail') else payment.user.username],
        ['Email', payment.user.email],
        ['Total Pembayaran', f'Rp {payment.total:,.0f}'],
        ['Jumlah Buku', str(payment.jumlah_buku)],
        ['Status', status],
        ['Disetujui Oleh', payment.pemroses or '-'],
        ['Tanggal Masuk', payment.created_at.strftime('%d %B %Y %H:%M WIB')],
    ]

    response = _build_receipt_pdf(
        f'bukti-pembayaran-{payment.payment}.pdf',
        'Bukti Pembayaran',
        fields,
    )
    _log_activity(request, 'payments', f'Mengunduh bukti pembayaran {payment.payment}.')
    return response


def donation_receipt_pdf(request, donation_id):
    blocked = _ensure_cms_access(request, 'donations')
    if blocked:
        return blocked

    donation = get_object_or_404(MyDonation, pk=donation_id)
    if donation.is_verified:
        status = 'Disetujui'
    elif donation.is_canceled:
        status = 'Ditolak'
    else:
        status = 'Menunggu'

    fields = [
        ['Nama Donatur', donation.initial],
        ['Email', donation.email],
        ['Nilai Donasi', f'Rp {donation.nilai:,.0f}'],
        ['Keterangan', donation.keterangan or '-'],
        ['Status', status],
        ['Disetujui Oleh', donation.pemroses or '-'],
        ['Tanggal Masuk', donation.created_at.strftime('%d %B %Y %H:%M WIB')],
    ]

    response = _build_receipt_pdf(
        f'bukti-donasi-{donation.donation}.pdf',
        'Bukti Donasi',
        fields,
    )
    _log_activity(request, 'donations', f'Mengunduh bukti donasi dari {donation.initial}.')
    return response


def _persist_book(book, new_pdf_uploaded):
    if new_pdf_uploaded:
        book.is_update_pdf = True
        book.is_update_info = False
    else:
        book.is_update_info = True
        book.is_update_pdf = False
    book.save()


def books_dashboard(request):
    blocked = _ensure_cms_access(request, 'books')
    if blocked:
        return blocked

    query = request.GET.get('q', '').strip()
    kategori_filter = request.GET.get('kategori', '').strip()

    purchased = UserBook.objects.filter(id_book=OuterRef('pk'))
    ordered = MyPaymentDetail.objects.filter(book=OuterRef('pk'))
    books = (Books.objects.select_related('kategori')
             .annotate(has_purchase=Exists(purchased) | Exists(ordered))
             .order_by('-created_at'))

    if query:
        books = books.filter(
            Q(judul__icontains=query) | Q(pengarang__icontains=query) | Q(isbn__icontains=query)
        )

    if kategori_filter:
        books = books.filter(kategori_id=kategori_filter)

    paginator = Paginator(books, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'current_query': query,
        'current_kategori': kategori_filter,
        'categories': Category.objects.all().order_by('nama'),
        'total_books': Books.objects.count(),
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Management Buku', None)),
    }
    return render(request, 'cms/books_dashboard.html', context)


@require_POST
def book_toggle_active(request, book_id):
    """Switch a book on/off. Off = hidden from catalogue/search/API and not purchasable;
    people who already own it keep reading it from Koleksiku."""
    blocked = _ensure_cms_access(request, 'books')
    if blocked:
        return blocked
    book = get_object_or_404(Books, pk=book_id)
    new_state = not book.is_active
    # queryset.update(): Books.save() has custom branches and must not run here
    Books.objects.filter(pk=book.pk).update(is_active=new_state)
    label = 'diaktifkan (tampil di katalog)' if new_state else 'dinonaktifkan (disembunyikan dari katalog; pemilik buku tetap bisa membaca)'
    messages.add_message(request, messages.SUCCESS, f'Buku "{book.judul}" {label}.')
    _log_activity(request, 'books', f'Buku "{book.judul}" {label}.')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER') or '/cms/books/')


@require_POST
def book_delete(request, book_id):
    """Delete a book that has never been bought or ordered. Refused otherwise."""
    blocked = _ensure_cms_access(request, 'books')
    if blocked:
        return blocked
    book = get_object_or_404(Books, pk=book_id)
    if UserBook.objects.filter(id_book=book).exists() or MyPaymentDetail.objects.filter(book=book).exists():
        messages.add_message(request, messages.SUCCESS,
                             f'Buku "{book.judul}" sudah pernah dibeli/dipesan sehingga tidak bisa dihapus. Nonaktifkan saja.')
        return HttpResponseRedirect('/cms/books/')
    title, pk = book.judul, str(book.pk)
    pdf_name = book.pdf_full.name if book.pdf_full else None
    try:
        with transaction.atomic():
            book.delete()
    except (RestrictedError, ProtectedError):
        messages.add_message(request, messages.SUCCESS,
                             f'Buku "{title}" masih punya review pembaca sehingga tidak bisa dihapus. Nonaktifkan saja.')
        return HttpResponseRedirect('/cms/books/')
    # files go only after the DB delete succeeded
    media = settings.MEDIA_ROOT
    shutil.rmtree(os.path.join(media, 'extract', 'pdf_full', pk), ignore_errors=True)
    for name in os.listdir(os.path.join(media, 'thumbs')) if os.path.isdir(os.path.join(media, 'thumbs')) else []:
        if name.startswith(pk + '_'):
            try:
                os.remove(os.path.join(media, 'thumbs', name))
            except OSError:
                pass
    if pdf_name:
        try:
            os.remove(os.path.join(media, pdf_name))
        except OSError:
            pass
    messages.add_message(request, messages.SUCCESS, f'Buku "{title}" berhasil dihapus.')
    _log_activity(request, 'books', f'Menghapus buku "{title}".')
    return HttpResponseRedirect('/cms/books/')


def book_pdf_progress(request, book_id):
    blocked = _ensure_cms_access(request, 'books')
    if blocked:
        return blocked
    return JsonResponse(read_progress(book_id))


def book_form(request, book_id=None):
    blocked = _ensure_cms_access(request, 'books')
    if blocked:
        return blocked

    book = None
    if book_id:
        book = get_object_or_404(Books, pk=book_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            new_pdf_uploaded = bool(request.FILES.get('pdf_full'))
            is_new_book = book is None
            instance = form.save(commit=False)
            if new_pdf_uploaded and is_ajax:
                # Konversi PDF lama bisa melewati timeout gateway: simpan dulu, proses di background.
                if is_new_book:
                    instance.is_active = False  # aktif otomatis setelah konversi sukses
                _persist_book(instance, False)
                start_pdf_conversion(instance, activate=is_new_book)
                action = 'Menambahkan' if is_new_book else 'Mengubah'
                _log_activity(request, 'books', f'{action} buku "{instance.judul}" (PDF diproses di background).')
                return JsonResponse({'ok': True, 'book_id': str(instance.pk), 'judul': instance.judul,
                                     'redirect': '/cms/books/'})
            _persist_book(instance, new_pdf_uploaded)
            if is_ajax:
                messages.add_message(request, messages.SUCCESS, f'Buku "{instance.judul}" berhasil disimpan.')
                return JsonResponse({'ok': True, 'redirect': '/cms/books/'})
            messages.add_message(request, messages.SUCCESS, f'Buku "{instance.judul}" berhasil disimpan.')
            action = 'Menambahkan' if is_new_book else 'Mengubah'
            _log_activity(request, 'books', f'{action} buku "{instance.judul}".')
            return HttpResponseRedirect('/cms/books/')
        if is_ajax:
            return JsonResponse({'ok': False, 'errors': {k: [str(e) for e in v] for k, v in form.errors.items()}},
                                status=400)
        messages.add_message(request, messages.SUCCESS, 'Data buku gagal disimpan, periksa kembali form.')
    else:
        form = BookForm(instance=book)

    context = {
        'form': form,
        'book': book,
        'breadcrumbs': _breadcrumbs(
            ('CMS', '/cms/'),
            ('Management Buku', '/cms/books/'),
            ('Edit Buku' if book else 'Tambah Buku', None),
        ),
    }
    return render(request, 'cms/book_form.html', context)


def categories_dashboard(request):
    blocked = _ensure_cms_access(request, 'categories')
    if blocked:
        return blocked

    query = request.GET.get('q', '').strip()
    categories = Category.objects.annotate(book_count=Count('books')).order_by('nama')
    if query:
        categories = categories.filter(nama__icontains=query)

    context = {
        'categories': categories,
        'current_query': query,
        'total_categories': Category.objects.count(),
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Master Kategori', None)),
    }
    return render(request, 'cms/categories_dashboard.html', context)


def category_form(request, category_id=None):
    blocked = _ensure_cms_access(request, 'categories')
    if blocked:
        return blocked

    category = None
    if category_id:
        category = get_object_or_404(Category, pk=category_id)

    if request.method == 'POST':
        if request.POST.get('action') == 'delete' and category is not None:
            if category.books_set.exists():
                messages.add_message(request, messages.SUCCESS, f'Kategori "{category.nama}" masih dipakai oleh buku dan tidak dapat dihapus.')
                return HttpResponseRedirect(f"/cms/categories/{category_id}/edit/")
            category_name = category.nama
            category.delete()
            messages.add_message(request, messages.SUCCESS, 'Kategori berhasil dihapus.')
            _log_activity(request, 'categories', f'Menghapus kategori "{category_name}".')
            return HttpResponseRedirect('/cms/categories/')

        is_new_category = category is None
        form = CategoryQuickForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            instance = form.save()
            messages.add_message(request, messages.SUCCESS, f'Kategori "{instance.nama}" berhasil disimpan.')
            action = 'Menambahkan' if is_new_category else 'Mengubah'
            _log_activity(request, 'categories', f'{action} kategori "{instance.nama}".')
            return HttpResponseRedirect('/cms/categories/')
        messages.add_message(request, messages.SUCCESS, 'Kategori gagal disimpan, periksa kembali form.')
    else:
        form = CategoryQuickForm(instance=category)

    context = {
        'form': form,
        'category': category,
        'breadcrumbs': _breadcrumbs(
            ('CMS', '/cms/'),
            ('Master Kategori', '/cms/categories/'),
            ('Edit Kategori' if category else 'Tambah Kategori', None),
        ),
    }
    return render(request, 'cms/category_form.html', context)


def instagram_settings_dashboard(request):
    blocked = _ensure_cms_access(request, 'instagram_settings')
    if blocked:
        return blocked

    photos = Instagram.objects.all().order_by('-id')
    photo_rows = [{'photo': photo, 'form': InstagramForm(instance=photo)} for photo in photos]

    context = {
        'photo_rows': photo_rows,
        'total_photos': len(photo_rows),
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Pengaturan Instagram', None)),
    }
    return render(request, 'cms/instagram_settings_dashboard.html', context)


def instagram_settings_form(request, photo_id=None):
    blocked = _ensure_cms_access(request, 'instagram_settings')
    if blocked:
        return blocked

    photo = None
    if photo_id:
        photo = get_object_or_404(Instagram, pk=photo_id)

    if request.method == 'POST':
        if request.POST.get('action') == 'delete' and photo is not None:
            photo.delete()
            messages.add_message(request, messages.SUCCESS, 'Foto Instagram berhasil dihapus.')
            _log_activity(request, 'instagram_settings', f'Menghapus foto Instagram #{photo_id}.')
            return HttpResponseRedirect('/cms/instagram/')

        is_new_photo = photo is None
        form = InstagramForm(request.POST, request.FILES, instance=photo)
        if form.is_valid():
            instance = form.save()
            messages.add_message(request, messages.SUCCESS, 'Foto Instagram berhasil disimpan.')
            action = 'Menambahkan' if is_new_photo else 'Mengubah'
            _log_activity(request, 'instagram_settings', f'{action} foto Instagram #{instance.pk}.')
            return HttpResponseRedirect('/cms/instagram/')
        messages.add_message(request, messages.SUCCESS, 'Foto Instagram gagal disimpan, periksa kembali form.')
        if not is_new_photo:
            return HttpResponseRedirect('/cms/instagram/')
    else:
        form = InstagramForm(instance=photo)

    context = {
        'form': form,
        'photo': photo,
        'breadcrumbs': _breadcrumbs(
            ('CMS', '/cms/'),
            ('Pengaturan Instagram', '/cms/instagram/'),
            ('Edit Foto' if photo else 'Tambah Foto', None),
        ),
    }
    return render(request, 'cms/instagram_settings_form.html', context)


def pengumuman_settings_dashboard(request):
    blocked = _ensure_cms_access(request, 'pengumuman_settings')
    if blocked:
        return blocked

    current = Pengumuman.objects.order_by('-id').first()

    if request.method == 'POST':
        form = PengumumanForm(request.POST, instance=current)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.SUCCESS, 'Teks pengumuman berhasil disimpan.')
            _log_activity(request, 'pengumuman_settings', 'Mengubah teks pengumuman.')
            return HttpResponseRedirect('/cms/pengumuman/')
        messages.add_message(request, messages.SUCCESS, 'Teks pengumuman gagal disimpan, periksa kembali form.')
    else:
        form = PengumumanForm(instance=current)

    context = {
        'form': form,
        'preview_text': get_pengumuman_text(),
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Pengaturan Pengumuman', None)),
    }
    return render(request, 'cms/pengumuman_settings.html', context)


def qris_settings_dashboard(request):
    blocked = _ensure_cms_access(request, 'qris_settings')
    if blocked:
        return blocked

    tujuan_labels = dict(QrisCode.TUJUAN_CHOICES)
    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        if action == 'upload':
            form = QrisUploadForm(request.POST, request.FILES)
            if form.is_valid():
                tujuan, f = form.cleaned_data['tujuan'], form.cleaned_data['gambar']
                f.name = f'{uuid.uuid4()}.{f.ext}'
                with transaction.atomic():
                    QrisCode.objects.filter(tujuan=tujuan, is_active=True).update(is_active=False)
                    QrisCode.objects.create(tujuan=tujuan, gambar=f, is_active=True,
                                            keterangan=form.cleaned_data['keterangan'].strip(),
                                            pemroses=request.user.get_username())
                messages.add_message(request, messages.SUCCESS, f'QRIS {tujuan_labels[tujuan]} berhasil diganti.')
                _log_activity(request, 'qris_settings', f'Mengganti QRIS {tujuan_labels[tujuan]}.')
            else:
                err = '; '.join(e for errs in form.errors.values() for e in errs)
                messages.add_message(request, messages.SUCCESS, f'QRIS gagal diunggah: {err}')
        elif action in ('activate', 'delete'):
            raw = request.POST.get('id', '').strip()
            item = QrisCode.objects.filter(pk=int(raw)).first() if raw.isdigit() else None
            if item is None:
                messages.add_message(request, messages.SUCCESS, 'QRIS tidak ditemukan.')
            elif action == 'activate':
                with transaction.atomic():
                    QrisCode.objects.filter(tujuan=item.tujuan, is_active=True).update(is_active=False)
                    item.is_active = True
                    item.save(update_fields=['is_active'])
                messages.add_message(request, messages.SUCCESS, f'QRIS {tujuan_labels[item.tujuan]} diaktifkan kembali.')
                _log_activity(request, 'qris_settings', f'Mengaktifkan kembali QRIS {tujuan_labels[item.tujuan]} #{item.pk}.')
            elif item.is_active:
                messages.add_message(request, messages.SUCCESS, 'QRIS yang sedang aktif tidak bisa dihapus. Aktifkan QRIS lain terlebih dahulu.')
            else:
                item.gambar.delete(save=False)
                item.delete()
                messages.add_message(request, messages.SUCCESS, 'QRIS dihapus dari riwayat.')
                _log_activity(request, 'qris_settings', f'Menghapus riwayat QRIS {tujuan_labels[item.tujuan]}.')
        return HttpResponseRedirect('/cms/qris/')

    sections = []
    for key, label in QrisCode.TUJUAN_CHOICES:
        ensure_default_qris(key)  # tampilkan QRIS bawaan bila belum pernah ada yang diunggah
        rows = list(QrisCode.objects.filter(tujuan=key))
        sections.append({
            'key': key, 'label': label,
            'active': next((r for r in rows if r.is_active), None),
            'history': [r for r in rows if not r.is_active],
            'form': QrisUploadForm(initial={'tujuan': key}),
        })
    context = {
        'sections': sections,
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('QRIS Pembayaran', None)),
    }
    return render(request, 'cms/qris_settings.html', context)


def _revenue_share_rows(month, year):
    """Per buku: jumlah terjual, pendapatan, bagian penulis & Litanas dari pembayaran yang disetujui
    pada periode (acuan tanggal sama dengan laporan pembayaran: tanggal masuk invoice)."""
    rows = (MyPaymentDetail.objects
            .filter(payment__is_verified=True, payment__is_canceled=False,
                    payment__created_at__year=year, payment__created_at__month=month, book__isnull=False)
            .values('book_id', 'book__judul', 'book__pengarang', 'book__persen_penulis', 'book__persen_litanas')
            .annotate(terjual=Count('id'), pendapatan=Sum('harga'),
                      penulis=Sum('bagian_penulis'), litanas=Sum('bagian_litanas'))
            .order_by('-pendapatan', 'book__judul'))
    return list(rows)


def revenue_share_dashboard(request):
    blocked = _ensure_cms_access(request, 'reports')
    if blocked:
        return blocked

    month, year = _report_period(request)
    rows = _revenue_share_rows(month, year)
    totals = {
        'terjual': sum(r['terjual'] for r in rows),
        'pendapatan': sum(r['pendapatan'] or 0 for r in rows),
        'penulis': sum(r['penulis'] or 0 for r in rows),
        'litanas': sum(r['litanas'] or 0 for r in rows),
    }
    context = {
        'rows': rows, 'totals': totals,
        'report_month': month, 'report_year': year,
        'month_choices': MONTH_CHOICES, 'year_choices': _year_choices(),
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Bagi Hasil', None)),
    }
    return render(request, 'cms/revenue_share.html', context)


def revenue_share_export(request):
    blocked = _ensure_cms_access(request, 'reports')
    if blocked:
        return blocked
    month, year = _report_period(request)
    rows = [[r['book__judul'], r['book__pengarang'], r['terjual'], float(r['pendapatan'] or 0),
             float(r['penulis'] or 0), float(r['litanas'] or 0)] for r in _revenue_share_rows(month, year)]
    response = _xlsx_response(f'bagi-hasil-{year}-{month:02d}.xlsx',
                              ['Buku', 'Penulis', 'Terjual', 'Pendapatan', 'Bagian Penulis', 'Bagian Litanas'], rows)
    _log_activity(request, 'revenue_share', f'Mengunduh laporan bagi hasil periode {dict(MONTH_CHOICES).get(month, month)} {year}.')
    return response


def broadcast_dashboard(request):
    blocked = _ensure_cms_access(request, 'broadcast')
    if blocked:
        return blocked

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        if action in ('toggle', 'delete'):
            raw_id = request.POST.get('id', '').strip()
            item = MobileBroadcast.objects.filter(pk=int(raw_id)).first() if raw_id.isdigit() else None
            if item:
                if action == 'toggle':
                    item.is_active = not item.is_active
                    item.save(update_fields=['is_active'])
                    messages.add_message(request, messages.SUCCESS, 'Status notifikasi diperbarui.')
                else:
                    item.delete()
                    messages.add_message(request, messages.SUCCESS, 'Notifikasi dihapus.')
                _log_activity(request, 'broadcast', f'{action} notifikasi aplikasi: {item.header}')
            return HttpResponseRedirect('/cms/broadcast/')
        form = MobileBroadcastForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.add_message(request, messages.SUCCESS, 'Notifikasi disimpan; akan muncul di HP pengguna dalam beberapa menit.')
            _log_activity(request, 'broadcast', f'Membuat notifikasi aplikasi: {item.header}')
            return HttpResponseRedirect('/cms/broadcast/')
    else:
        form = MobileBroadcastForm()

    context = {
        'form': form,
        'items': MobileBroadcast.objects.all()[:50],
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Notifikasi Aplikasi', None)),
    }
    return render(request, 'cms/broadcast.html', context)


def promo_bestseller_dashboard(request):
    blocked = _ensure_cms_access(request, 'promo_bestseller')
    if blocked:
        return blocked

    tab = request.GET.get('tab', 'promo')
    if tab not in ('promo', 'bestseller'):
        tab = 'promo'

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()

        if action == 'toggle_promo':
            promo_id = request.POST.get('promo_id', '').strip()
            try:
                promo = OnSaleBook.objects.get(pk=promo_id)
                promo.is_active = not promo.is_active
                promo.save()
                status_text = 'diaktifkan' if promo.is_active else 'dinonaktifkan'
                messages.add_message(request, messages.SUCCESS, f'Promo "{promo.header}" berhasil {status_text}.')
                _log_activity(request, 'promo_bestseller', f'Mengubah promo "{promo.header}" menjadi {status_text}.')
            except OnSaleBook.DoesNotExist:
                messages.add_message(request, messages.SUCCESS, 'Promo tidak ditemukan.')
            return HttpResponseRedirect('/cms/promo/?tab=promo')

        if action == 'delete_promo':
            promo_id = request.POST.get('promo_id', '').strip()
            promo = OnSaleBook.objects.filter(pk=promo_id).first()
            promo_header = promo.header if promo else promo_id
            OnSaleBook.objects.filter(pk=promo_id).delete()
            messages.add_message(request, messages.SUCCESS, 'Promo berhasil dihapus.')
            _log_activity(request, 'promo_bestseller', f'Menghapus promo "{promo_header}".')
            return HttpResponseRedirect('/cms/promo/?tab=promo')

        if action == 'toggle_bestseller':
            book_id = request.POST.get('book_id', '').strip()
            query = request.POST.get('q', '')
            kategori_filter = request.POST.get('kategori', '')
            try:
                book = Books.objects.get(pk=book_id)
                book.is_best_seller = not book.is_best_seller
                _persist_book(book, new_pdf_uploaded=False)
                status_text = 'ditambahkan ke' if book.is_best_seller else 'dihapus dari'
                messages.add_message(request, messages.SUCCESS, f'"{book.judul}" berhasil {status_text} daftar best seller.')
                _log_activity(request, 'promo_bestseller', f'"{book.judul}" {status_text} daftar best seller.')
            except Books.DoesNotExist:
                messages.add_message(request, messages.SUCCESS, 'Buku tidak ditemukan.')
            return HttpResponseRedirect(f"/cms/promo/?tab=bestseller&q={query}&kategori={kategori_filter}")

    context = {
        'active_tab': tab,
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Promo & Best Seller', None)),
    }

    if tab == 'bestseller':
        query = request.GET.get('q', '').strip()
        kategori_filter = request.GET.get('kategori', '').strip()

        books = Books.objects.select_related('kategori').order_by('-updated_at')
        if query:
            books = books.filter(Q(judul__icontains=query) | Q(pengarang__icontains=query))
        if kategori_filter:
            books = books.filter(kategori_id=kategori_filter)

        paginator = Paginator(books, 15)
        page_obj = paginator.get_page(request.GET.get('page'))

        context.update({
            'page_obj': page_obj,
            'current_query': query,
            'current_kategori': kategori_filter,
            'categories': Category.objects.all().order_by('nama'),
            'best_seller_count': Books.objects.filter(is_best_seller=True).count(),
        })
    else:
        promos = OnSaleBook.objects.select_related('book', 'book__kategori').order_by('-created_at')
        promo_paginator = Paginator(promos, 10)
        context['promo_page_obj'] = promo_paginator.get_page(request.GET.get('page'))
        context['promo_active_count'] = promos.filter(is_active=True).count()

    return render(request, 'cms/promo_bestseller.html', context)


def onsale_form(request, promo_id=None):
    blocked = _ensure_cms_access(request, 'promo_bestseller')
    if blocked:
        return blocked

    promo = None
    if promo_id:
        promo = get_object_or_404(OnSaleBook, pk=promo_id)

    if request.method == 'POST':
        is_new_promo = promo is None
        form = OnSaleForm(request.POST, instance=promo)
        if form.is_valid():
            instance = form.save()
            messages.add_message(request, messages.SUCCESS, f'Promo "{instance.header}" berhasil disimpan.')
            action = 'Menambahkan' if is_new_promo else 'Mengubah'
            _log_activity(request, 'promo_bestseller', f'{action} promo "{instance.header}".')
            return HttpResponseRedirect('/cms/promo/?tab=promo')
        messages.add_message(request, messages.SUCCESS, 'Promo gagal disimpan, periksa kembali form.')
    else:
        form = OnSaleForm(instance=promo)

    context = {
        'form': form,
        'promo': promo,
        'breadcrumbs': _breadcrumbs(
            ('CMS', '/cms/'),
            ('Promo & Best Seller', '/cms/promo/'),
            ('Edit Promo' if promo else 'Tambah Promo', None),
        ),
    }
    return render(request, 'cms/onsale_form.html', context)


def customers_dashboard(request):
    blocked = _ensure_cms_access(request, 'customers')
    if blocked:
        return blocked

    if request.method == 'POST':
        user_id = request.POST.get('user_id', '').strip()
        query = request.POST.get('q', '')
        page = request.POST.get('page', '1')
        try:
            customer = User.objects.get(pk=user_id, is_superuser=False)
            customer.is_active = not customer.is_active
            customer.save()
            status_text = 'diaktifkan' if customer.is_active else 'dinonaktifkan'
            messages.add_message(request, messages.SUCCESS, f'Akun "{customer.username}" berhasil {status_text}.')
            _log_activity(request, 'customers', f'Akun pelanggan "{customer.username}" {status_text}.')
        except User.DoesNotExist:
            messages.add_message(request, messages.SUCCESS, 'Pelanggan tidak ditemukan.')
        return HttpResponseRedirect(f"/cms/customers/?q={query}&page={page}")

    query = request.GET.get('q', '').strip()

    customers = User.objects.filter(is_superuser=False, groups__isnull=True).order_by('-date_joined')

    if query:
        customers = customers.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(userdetail__nama_lengkap__icontains=query)
            | Q(userdetail__no_whatsapp__icontains=query)
        )

    paginator = Paginator(customers, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'current_query': query,
        'total_customers': User.objects.filter(is_superuser=False, groups__isnull=True).count(),
        'active_customers': User.objects.filter(is_superuser=False, groups__isnull=True, is_active=True).count(),
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Management Pelanggan', None)),
    }
    return render(request, 'cms/customers_dashboard.html', context)


def content_moderation_dashboard(request):
    blocked = _ensure_cms_access(request, 'content_moderation')
    if blocked:
        return blocked

    tab = request.GET.get('tab', 'coretan')
    if tab not in ('coretan', 'sahabat', 'buku'):
        tab = 'coretan'

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()

        if action == 'toggle_coretan':
            blog_id = request.POST.get('blog_id', '').strip()
            try:
                blog = Blogs.objects.get(pk=blog_id, tipe='Coretan Pena')
                blog.is_active = not blog.is_active
                blog.save()
                status_text = 'diaktifkan' if blog.is_active else 'dinonaktifkan'
                messages.add_message(request, messages.SUCCESS, f'Coretan pena "{blog.header}" berhasil {status_text}.')
                _log_activity(request, 'content_moderation', f'Coretan pena "{blog.header}" {status_text}.')
            except Blogs.DoesNotExist:
                messages.add_message(request, messages.SUCCESS, 'Coretan pena tidak ditemukan.')
            return HttpResponseRedirect('/cms/content/?tab=coretan')

        if action == 'toggle_sahabat':
            review_id = request.POST.get('review_id', '').strip()
            try:
                review = PageReview.objects.get(pk=review_id)
                review.is_active = not review.is_active
                review.save()
                status_text = 'ditampilkan' if review.is_active else 'disembunyikan'
                messages.add_message(request, messages.SUCCESS, f'Review sahabat berhasil {status_text}.')
                _log_activity(request, 'content_moderation', f'Review sahabat #{review.pk} {status_text}.')
            except PageReview.DoesNotExist:
                messages.add_message(request, messages.SUCCESS, 'Review tidak ditemukan.')
            return HttpResponseRedirect('/cms/content/?tab=sahabat')

        if action == 'toggle_buku':
            review_id = request.POST.get('review_id', '').strip()
            try:
                review = BookComment.objects.get(pk=review_id)
                review.is_publish = not review.is_publish
                review.save()
                status_text = 'ditampilkan' if review.is_publish else 'disembunyikan'
                messages.add_message(request, messages.SUCCESS, f'Review buku berhasil {status_text}.')
                _log_activity(request, 'content_moderation', f'Review buku #{review.pk} {status_text}.')
            except BookComment.DoesNotExist:
                messages.add_message(request, messages.SUCCESS, 'Review tidak ditemukan.')
            return HttpResponseRedirect('/cms/content/?tab=buku')

    context = {
        'active_tab': tab,
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Moderasi Konten', None)),
    }

    if tab == 'coretan':
        queryset = Blogs.objects.filter(tipe='Coretan Pena').select_related('author').order_by('-created_at')
    elif tab == 'sahabat':
        queryset = PageReview.objects.select_related('user').order_by('-created_at')
    else:
        queryset = BookComment.objects.select_related('book', 'user', 'user__userdetail').order_by('-created_at')

    paginator = Paginator(queryset, 10)
    context['page_obj'] = paginator.get_page(request.GET.get('page'))

    return render(request, 'cms/content_moderation.html', context)


def roles_dashboard(request):
    blocked = _ensure_cms_access(request, 'roles')
    if blocked:
        return blocked

    form = CmsUserCreateForm()

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()

        if action == 'create_user':
            form = CmsUserCreateForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                new_user = User.objects.create_user(
                    username=data['username'],
                    email=data['email'],
                    password=data['password'],
                    first_name=data['nama_lengkap'][:30],
                )
                new_user.is_staff = True
                new_user.save()
                group = Group.objects.get(name=data['role'])
                new_user.groups.set([group])
                messages.add_message(
                    request, messages.SUCCESS,
                    f'Akun staff "{new_user.username}" berhasil dibuat dengan peran {data["role"]}.'
                )
                _log_activity(request, 'roles', f'Membuat akun staff "{new_user.username}" dengan peran {data["role"]}.')
                return HttpResponseRedirect('/cms/roles/')
            messages.add_message(request, messages.SUCCESS, 'Akun staff gagal dibuat, periksa kembali form.')

        elif action == 'change_role':
            user_id = request.POST.get('user_id', '').strip()
            new_role = request.POST.get('role', '').strip()
            try:
                staff_user = User.objects.get(pk=user_id, is_superuser=False)
                if new_role in CMS_ROLE_GROUPS:
                    group = Group.objects.get(name=new_role)
                    staff_user.groups.set([group])
                    messages.add_message(request, messages.SUCCESS, f'Peran "{staff_user.username}" berhasil diubah menjadi {new_role}.')
                    _log_activity(request, 'roles', f'Mengubah peran "{staff_user.username}" menjadi {new_role}.')
            except User.DoesNotExist:
                messages.add_message(request, messages.SUCCESS, 'Akun staff tidak ditemukan.')
            return HttpResponseRedirect('/cms/roles/')

        elif action == 'toggle_active':
            user_id = request.POST.get('user_id', '').strip()
            try:
                staff_user = User.objects.get(pk=user_id, is_superuser=False)
                staff_user.is_active = not staff_user.is_active
                staff_user.save()
                status_text = 'diaktifkan' if staff_user.is_active else 'dinonaktifkan'
                messages.add_message(request, messages.SUCCESS, f'Akun staff "{staff_user.username}" berhasil {status_text}.')
                _log_activity(request, 'roles', f'Akun staff "{staff_user.username}" {status_text}.')
            except User.DoesNotExist:
                messages.add_message(request, messages.SUCCESS, 'Akun staff tidak ditemukan.')
            return HttpResponseRedirect('/cms/roles/')

    staff_users = User.objects.filter(groups__name__in=CMS_ROLE_GROUPS).distinct().order_by('username')
    paginator = Paginator(staff_users, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    staff_rows = [
        {'user': staff_user, 'roles': list(staff_user.groups.values_list('name', flat=True))}
        for staff_user in page_obj
    ]

    context = {
        'form': form,
        'staff_rows': staff_rows,
        'page_obj': page_obj,
        'role_choices': CMS_ROLE_CHOICES,
        'superuser_accounts': User.objects.filter(is_superuser=True).order_by('username'),
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Role & User CMS', None)),
    }
    return render(request, 'cms/roles_dashboard.html', context)


def coretan_pena_dashboard(request):
    blocked = _ensure_cms_access(request, 'coretan_pena')
    if blocked:
        return blocked

    posts = Blogs.objects.filter(tipe='Coretan Pena', author=request.user).order_by('-created_at')
    paginator = Paginator(posts, 10)

    context = {
        'page_obj': paginator.get_page(request.GET.get('page')),
        'total_posts': posts.count(),
        'active_posts': posts.filter(is_active=True).count(),
        'pending_posts': posts.filter(is_active=False).count(),
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Coretan Pena', None)),
    }
    return render(request, 'cms/coretan_pena_dashboard.html', context)


def coretan_pena_form(request, blog_id=None):
    blocked = _ensure_cms_access(request, 'coretan_pena')
    if blocked:
        return blocked

    blog = None
    if blog_id:
        blog = get_object_or_404(Blogs, pk=blog_id, tipe='Coretan Pena')
        if blog.author_id != request.user.id:
            messages.add_message(request, messages.SUCCESS, 'Anda hanya dapat mengubah coretan pena milik Anda sendiri.')
            return HttpResponseRedirect('/cms/coretan-pena/')

    if request.method == 'POST':
        if request.POST.get('action') == 'delete' and blog is not None:
            blog_header = blog.header
            blog.delete()
            messages.add_message(request, messages.SUCCESS, 'Coretan pena berhasil dihapus.')
            _log_activity(request, 'coretan_pena', f'Menghapus coretan pena "{blog_header}".')
            return HttpResponseRedirect('/cms/coretan-pena/')

        is_new_post = blog is None
        form = CoretanPenaForm(request.POST, request.FILES, instance=blog)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.tipe = 'Coretan Pena'
            instance.author = request.user
            instance.is_active = False
            instance.save()
            messages.add_message(
                request, messages.SUCCESS,
                f'Coretan pena "{instance.header}" berhasil disimpan dan menunggu moderasi admin sebelum tampil.'
            )
            action = 'Menambahkan' if is_new_post else 'Mengubah'
            _log_activity(request, 'coretan_pena', f'{action} coretan pena "{instance.header}".')
            return HttpResponseRedirect('/cms/coretan-pena/')
        messages.add_message(request, messages.SUCCESS, 'Coretan pena gagal disimpan, periksa kembali form.')
    else:
        form = CoretanPenaForm(instance=blog)

    context = {
        'form': form,
        'blog': blog,
        'breadcrumbs': _breadcrumbs(
            ('CMS', '/cms/'),
            ('Coretan Pena', '/cms/coretan-pena/'),
            ('Edit Tulisan' if blog else 'Tulis Baru', None),
        ),
    }
    return render(request, 'cms/coretan_pena_form.html', context)


BLOG_MAX_PHOTOS = 20
BLOG_MAX_PHOTO_BYTES = 5 * 1024 * 1024


def _validate_blog_photos(files):
    """Periksa isi file dengan Pillow (bukan hanya ekstensi). Mengembalikan daftar pesan error."""
    from PIL import Image, UnidentifiedImageError
    errors = []
    if len(files) > BLOG_MAX_PHOTOS:
        errors.append(f'Maksimal {BLOG_MAX_PHOTOS} foto per unggahan.')
        return errors
    for f in files:
        if f.size > BLOG_MAX_PHOTO_BYTES:
            errors.append(f'Foto "{f.name}" melebihi 5 MB.')
            continue
        try:
            img = Image.open(f)
            if img.format not in ('JPEG', 'PNG', 'WEBP'):
                errors.append(f'Foto "{f.name}" harus berformat JPG, PNG, atau WEBP.')
            img.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            errors.append(f'File "{f.name}" bukan gambar yang valid.')
        finally:
            f.seek(0)
    return errors


def blog_posts_dashboard(request):
    blocked = _ensure_cms_access(request, 'blog_posts')
    if blocked:
        return blocked

    # seperti daftar Post di WordPress: blog tayang dan blog arsip ditampilkan terpisah
    status = 'arsip' if request.GET.get('status') == 'arsip' else 'tayang'
    posts = BlogPost.objects.prefetch_related('images').filter(is_archived=(status == 'arsip')).order_by('-created_at')
    paginator = Paginator(posts, 10)

    all_posts = BlogPost.objects.all()
    context = {
        'page_obj': paginator.get_page(request.GET.get('page')),
        'status': status,
        'active_posts': all_posts.filter(is_archived=False).count(),
        'archived_posts': all_posts.filter(is_archived=True).count(),
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Blogs', None)),
    }
    return render(request, 'cms/blog_posts_dashboard.html', context)


def blog_post_form(request, post_id=None):
    blocked = _ensure_cms_access(request, 'blog_posts')
    if blocked:
        return blocked

    post = get_object_or_404(BlogPost, pk=post_id) if post_id else None

    if request.method == 'POST':
        if request.POST.get('action') == 'delete' and post is not None:
            judul = post.judul
            for img in post.images.all():
                img.image.delete(save=False)
            post.delete()
            messages.add_message(request, messages.SUCCESS, 'Blog berhasil dihapus.')
            _log_activity(request, 'blog_posts', f'Menghapus blog "{judul}".')
            return HttpResponseRedirect('/cms/blogs/')

        if request.POST.get('action') == 'toggle_archive' and post is not None:
            post.is_archived = not post.is_archived
            post.save(update_fields=['is_archived', 'updated_at'])
            label = 'disembunyikan dari halaman utama (diarsipkan)' if post.is_archived else 'ditampilkan di halaman utama'
            messages.add_message(request, messages.SUCCESS, f'Blog "{post.judul}" {label}.')
            _log_activity(request, 'blog_posts', f'Blog "{post.judul}" {label}.')
            return HttpResponseRedirect(request.POST.get('next') or '/cms/blogs/')

        is_new = post is None
        form = BlogPostForm(request.POST, instance=post)
        photos = request.FILES.getlist('photos')
        photo_errors = _validate_blog_photos(photos)
        if form.is_valid() and not photo_errors:
            with transaction.atomic():
                instance = form.save(commit=False)
                if is_new:
                    instance.created_by = request.user
                instance.save()
                if post is not None:
                    for img in instance.images.filter(pk__in=request.POST.getlist('remove_images')):
                        img.image.delete(save=False)
                        img.delete()
                for f in photos:
                    BlogPostImage.objects.create(post=instance, image=f)
            messages.add_message(request, messages.SUCCESS, f'Blog "{instance.judul}" berhasil disimpan.')
            _log_activity(request, 'blog_posts', f"{'Menambahkan' if is_new else 'Mengubah'} blog \"{instance.judul}\".")
            return HttpResponseRedirect('/cms/blogs/')
        for err in photo_errors:
            messages.add_message(request, messages.SUCCESS, err)
        messages.add_message(request, messages.SUCCESS, 'Blog gagal disimpan, periksa kembali form.')
    else:
        form = BlogPostForm(instance=post)

    context = {
        'form': form,
        'post': post,
        'max_photos': BLOG_MAX_PHOTOS,
        'breadcrumbs': _breadcrumbs(
            ('CMS', '/cms/'), ('Blogs', '/cms/blogs/'),
            ('Edit Blog' if post else 'Tulis Blog', None),
        ),
    }
    return render(request, 'cms/blog_post_form.html', context)


def notifications_dashboard(request):
    blocked = _ensure_cms_access(request)
    if blocked:
        return blocked

    is_super = request.user.is_superuser
    roles = _user_cms_roles(request.user)
    all_notifications = get_notifications(request.user, is_super, roles)

    paginator = Paginator(all_notifications, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'total_notifications': len(all_notifications),
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Notifikasi', None)),
    }
    return render(request, 'cms/notifications_dashboard.html', context)


def notification_detail(request, kind, pk):
    blocked = _ensure_cms_access(request)
    if blocked:
        return blocked

    is_super = request.user.is_superuser
    roles = _user_cms_roles(request.user)
    allowed_roles = NOTIFICATION_KIND_ROLES.get(kind)

    if allowed_roles is None or not (is_super or (roles & allowed_roles)):
        messages.add_message(request, messages.SUCCESS, 'Anda tidak memiliki akses ke notifikasi ini.')
        return HttpResponseRedirect('/cms/notifications/')

    can_process = _can_process_finance(request)

    context = {
        'kind': kind,
        'can_process': can_process,
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Notifikasi', '/cms/notifications/'), ('Detail Notifikasi', None)),
    }

    if kind == 'payment':
        payment = get_object_or_404(MyPayment, pk=pk)
        if request.method == 'POST' and not payment.is_verified and not payment.is_canceled:
            if not can_process:
                messages.add_message(request, messages.SUCCESS, 'Hanya akun dengan peran Keuangan yang dapat memproses persetujuan pembayaran.')
                return HttpResponseRedirect('/cms/notifications/')
            decision = request.POST.get('decision', '').strip()
            if decision == 'approve':
                payment.is_verified = True
                payment.is_canceled = False
                payment.pemroses = request.user.username
                payment.save()
                messages.add_message(request, messages.SUCCESS, f'Pembayaran {payment.payment} berhasil disetujui.')
                _log_activity(request, 'payments', f'Menyetujui pembayaran {payment.payment}.')
            elif decision == 'reject':
                payment.is_verified = False
                payment.is_canceled = True
                payment.pemroses = request.user.username
                payment.save()
                messages.add_message(request, messages.SUCCESS, f'Pembayaran {payment.payment} berhasil ditolak.')
                _log_activity(request, 'payments', f'Menolak pembayaran {payment.payment}.')
            return HttpResponseRedirect('/cms/notifications/')
        context['payment'] = payment
        context['payment_details'] = MyPaymentDetail.objects.select_related('book').filter(payment=payment)

    elif kind == 'donation':
        donation = get_object_or_404(MyDonation, pk=pk)
        if request.method == 'POST' and not donation.is_verified and not donation.is_canceled:
            if not can_process:
                messages.add_message(request, messages.SUCCESS, 'Hanya akun dengan peran Keuangan yang dapat memproses persetujuan donasi.')
                return HttpResponseRedirect('/cms/notifications/')
            decision = request.POST.get('decision', '').strip()
            if decision == 'approve':
                donation.is_verified = True
                donation.is_canceled = False
                donation.pemroses = request.user.username
                donation.save()
                messages.add_message(request, messages.SUCCESS, f'Donasi dari {donation.initial} berhasil disetujui.')
                _log_activity(request, 'donations', f'Menyetujui donasi dari {donation.initial}.')
            elif decision == 'reject':
                donation.is_verified = False
                donation.is_canceled = True
                donation.pemroses = request.user.username
                donation.save()
                messages.add_message(request, messages.SUCCESS, f'Donasi dari {donation.initial} berhasil ditolak.')
                _log_activity(request, 'donations', f'Menolak donasi dari {donation.initial}.')
            return HttpResponseRedirect('/cms/notifications/')
        context['donation'] = donation

    elif kind == 'coretan_moderation':
        blog = get_object_or_404(Blogs, pk=pk, tipe='Coretan Pena')
        if request.method == 'POST':
            blog.is_active = not blog.is_active
            blog.save()
            status_text = 'diaktifkan' if blog.is_active else 'dinonaktifkan'
            messages.add_message(request, messages.SUCCESS, f'Coretan pena "{blog.header}" berhasil {status_text}.')
            _log_activity(request, 'content_moderation', f'Coretan pena "{blog.header}" {status_text}.')
            return HttpResponseRedirect('/cms/notifications/')
        context['blog'] = blog

    elif kind == 'review_sahabat':
        review = get_object_or_404(PageReview, pk=pk)
        if request.method == 'POST':
            review.is_active = not review.is_active
            review.save()
            status_text = 'ditampilkan' if review.is_active else 'disembunyikan'
            messages.add_message(request, messages.SUCCESS, f'Review sahabat berhasil {status_text}.')
            _log_activity(request, 'content_moderation', f'Review sahabat #{review.pk} {status_text}.')
            return HttpResponseRedirect('/cms/notifications/')
        context['review_sahabat'] = review

    elif kind == 'review_buku':
        review = get_object_or_404(BookComment, pk=pk)
        if request.method == 'POST':
            review.is_publish = not review.is_publish
            review.save()
            status_text = 'ditampilkan' if review.is_publish else 'disembunyikan'
            messages.add_message(request, messages.SUCCESS, f'Review buku berhasil {status_text}.')
            _log_activity(request, 'content_moderation', f'Review buku #{review.pk} {status_text}.')
            return HttpResponseRedirect('/cms/notifications/')
        context['review_buku'] = review

    elif kind == 'coretan_status':
        blog = get_object_or_404(Blogs, pk=pk, tipe='Coretan Pena', author=request.user)
        context['blog'] = blog

    else:
        messages.add_message(request, messages.SUCCESS, 'Notifikasi tidak dikenali.')
        return HttpResponseRedirect('/cms/notifications/')

    return render(request, 'cms/notification_detail.html', context)


MODULE_LABELS = {
    'payments': 'Payment',
    'donations': 'Donasi',
    'books': 'Buku',
    'categories': 'Kategori',
    'promo_bestseller': 'Promo & Best Seller',
    'customers': 'Pelanggan',
    'content_moderation': 'Moderasi Konten',
    'roles': 'Role & User',
    'coretan_pena': 'Coretan Pena',
}


def activity_log_dashboard(request):
    blocked = _ensure_cms_access(request, 'activity_log')
    if blocked:
        return blocked

    query = request.GET.get('q', '').strip()
    module_filter = request.GET.get('module', '').strip()

    logs = CmsActivityLog.objects.select_related('user').all()

    if module_filter:
        logs = logs.filter(module=module_filter)

    if query:
        logs = logs.filter(
            Q(action__icontains=query)
            | Q(user__username__icontains=query)
            | Q(ip_address__icontains=query)
        )

    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    for log in page_obj:
        log.module_label = MODULE_LABELS.get(log.module, log.module)

    context = {
        'page_obj': page_obj,
        'current_query': query,
        'current_module': module_filter,
        'module_choices': MODULE_LABELS,
        'total_logs': CmsActivityLog.objects.count(),
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Log Transaksi', None)),
    }
    return render(request, 'cms/activity_log_dashboard.html', context)
