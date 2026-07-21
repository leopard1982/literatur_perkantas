import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group, User
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from literatur.models import (
    Blogs, BookReview, Books, Category, MyDonation, MyPayment, MyPaymentDetail,
    OnSaleBook, PageReview, UserDetail,
)

from .forms import BookForm, CategoryQuickForm, CmsUserCreateForm, CoretanPenaForm, OnSaleForm
from .notifications import NOTIFICATION_KIND_ROLES, get_notifications
from .roles import CMS_ROLE_CHOICES, CMS_ROLE_GROUPS, ROLE_ACCESS, STRICT_ROLE_MODULES


CARD_CATALOG = [
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
        'module': 'roles',
        'title': 'Role & User CMS',
        'subtitle': 'Buat akun staff CMS dan atur peran akses.',
        'href': '/cms/roles/',
        'count_label': 'Akun Staff',
        'tone': 'gold',
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

        user = authenticate(request, username=username, password=password)

        if user is None:
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

        if module == 'payments':
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
                + BookReview.objects.filter(is_published=False).count()
            )
        elif module == 'roles':
            entry['count_value'] = User.objects.filter(groups__name__in=CMS_ROLE_GROUPS).distinct().count()
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
        summary_tiles.append({'label': 'Payment Pending', 'value': MyPayment.objects.filter(is_verified=False, is_canceled=False).count()})
        summary_tiles.append({'label': 'Payment Disetujui', 'value': MyPayment.objects.filter(is_verified=True).count()})
        summary_tiles.append({'label': 'Payment Ditolak', 'value': MyPayment.objects.filter(is_verified=False, is_canceled=True).count()})
    if has_access('donations'):
        summary_tiles.append({'label': 'Donasi Pending', 'value': MyDonation.objects.filter(is_verified=False, is_canceled=False).count()})
        summary_tiles.append({'label': 'Donasi Disetujui', 'value': MyDonation.objects.filter(is_verified=True).count()})
        summary_tiles.append({'label': 'Donasi Ditolak', 'value': MyDonation.objects.filter(is_verified=False, is_canceled=True).count()})

    context = {
        'cards': cards,
        'summary_tiles': summary_tiles,
        'roles': ['Superuser'] if is_super else sorted(roles),
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
    selected_invoice = request.GET.get('invoice', '').strip()

    if request.method == 'POST':
        payment_id = request.POST.get('payment_id', '').strip()
        decision = request.POST.get('decision', '').strip()

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
            elif decision == 'reject':
                payment.is_verified = False
                payment.is_canceled = True
                payment.pemroses = request.user.username
                payment.save()
                messages.add_message(request, messages.SUCCESS, f'Pembayaran {payment.payment} berhasil ditolak.')
        except Exception as ex:
            print(ex)
            messages.add_message(request, messages.SUCCESS, 'Terjadi kendala saat memproses status pembayaran.')

        return HttpResponseRedirect(
            f"/cms/payments/?status={status_filter}&q={query}&invoice={payment_id}"
        )

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

    selected_payment = None
    if selected_invoice:
        selected_payment = MyPayment.objects.select_related('user', 'user__userdetail').filter(payment=selected_invoice).first()

    if selected_payment is None and page_obj.object_list:
        selected_payment = page_obj.object_list[0]

    selected_details = []
    if selected_payment is not None:
        selected_details = MyPaymentDetail.objects.select_related('book').filter(payment=selected_payment)

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

    context = {
        'page_obj': page_obj,
        'selected_payment': selected_payment,
        'selected_details': selected_details,
        'current_status': status_filter,
        'current_query': query,
        'stats': stats,
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Management Payment', None)),
    }
    return render(request, 'cms/payment_dashboard.html', context)


def donation_dashboard(request):
    blocked = _ensure_cms_access(request, 'donations')
    if blocked:
        return blocked

    status_filter = request.GET.get('status', 'all').strip() or 'all'
    query = request.GET.get('q', '').strip()
    selected_id = request.GET.get('donation', '').strip()

    if request.method == 'POST':
        donation_id = request.POST.get('donation_id', '').strip()
        decision = request.POST.get('decision', '').strip()

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
            elif decision == 'reject':
                donation.is_verified = False
                donation.is_canceled = True
                donation.pemroses = request.user.username
                donation.save()
                messages.add_message(request, messages.SUCCESS, f'Donasi dari {donation.initial} berhasil ditolak.')
        except Exception as ex:
            print(ex)
            messages.add_message(request, messages.SUCCESS, 'Terjadi kendala saat memproses status donasi.')

        return HttpResponseRedirect(
            f"/cms/donations/?status={status_filter}&q={query}&donation={donation_id}"
        )

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

    selected_donation = None
    if selected_id:
        selected_donation = MyDonation.objects.filter(donation=selected_id).first()

    if selected_donation is None and page_obj.object_list:
        selected_donation = page_obj.object_list[0]

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

    context = {
        'page_obj': page_obj,
        'selected_donation': selected_donation,
        'current_status': status_filter,
        'current_query': query,
        'stats': stats,
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Management Donasi', None)),
    }
    return render(request, 'cms/donation_dashboard.html', context)


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

    books = Books.objects.select_related('kategori').order_by('-created_at')

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


def book_form(request, book_id=None):
    blocked = _ensure_cms_access(request, 'books')
    if blocked:
        return blocked

    book = None
    if book_id:
        book = get_object_or_404(Books, pk=book_id)

    category_form = CategoryQuickForm()

    if request.method == 'POST':
        if request.POST.get('form_name') == 'category':
            category_form = CategoryQuickForm(request.POST, request.FILES)
            if category_form.is_valid():
                category_form.save()
                messages.add_message(request, messages.SUCCESS, 'Kategori baru berhasil ditambahkan.')
            else:
                messages.add_message(request, messages.SUCCESS, 'Kategori gagal ditambahkan, periksa kembali data yang diisi.')
            redirect_url = f"/cms/books/{book_id}/edit/" if book_id else "/cms/books/add/"
            return HttpResponseRedirect(redirect_url)

        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            new_pdf_uploaded = bool(request.FILES.get('pdf_full'))
            instance = form.save(commit=False)
            _persist_book(instance, new_pdf_uploaded)
            messages.add_message(request, messages.SUCCESS, f'Buku "{instance.judul}" berhasil disimpan.')
            return HttpResponseRedirect('/cms/books/')
        messages.add_message(request, messages.SUCCESS, 'Data buku gagal disimpan, periksa kembali form.')
    else:
        form = BookForm(instance=book)

    context = {
        'form': form,
        'category_form': category_form,
        'book': book,
        'categories': Category.objects.all().order_by('nama'),
        'breadcrumbs': _breadcrumbs(
            ('CMS', '/cms/'),
            ('Management Buku', '/cms/books/'),
            ('Edit Buku' if book else 'Tambah Buku', None),
        ),
    }
    return render(request, 'cms/book_form.html', context)


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
            except OnSaleBook.DoesNotExist:
                messages.add_message(request, messages.SUCCESS, 'Promo tidak ditemukan.')
            return HttpResponseRedirect('/cms/promo/?tab=promo')

        if action == 'delete_promo':
            promo_id = request.POST.get('promo_id', '').strip()
            OnSaleBook.objects.filter(pk=promo_id).delete()
            messages.add_message(request, messages.SUCCESS, 'Promo berhasil dihapus.')
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
        form = OnSaleForm(request.POST, instance=promo)
        if form.is_valid():
            instance = form.save()
            messages.add_message(request, messages.SUCCESS, f'Promo "{instance.header}" berhasil disimpan.')
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
            except PageReview.DoesNotExist:
                messages.add_message(request, messages.SUCCESS, 'Review tidak ditemukan.')
            return HttpResponseRedirect('/cms/content/?tab=sahabat')

        if action == 'toggle_buku':
            review_id = request.POST.get('review_id', '').strip()
            try:
                review = BookReview.objects.get(pk=review_id)
                review.is_published = not review.is_published
                review.save()
                status_text = 'dipublikasikan' if review.is_published else 'disembunyikan'
                messages.add_message(request, messages.SUCCESS, f'Review buku berhasil {status_text}.')
            except BookReview.DoesNotExist:
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
        queryset = BookReview.objects.select_related('id_buku', 'id_customer').order_by('-updated_review')

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
            blog.delete()
            messages.add_message(request, messages.SUCCESS, 'Coretan pena berhasil dihapus.')
            return HttpResponseRedirect('/cms/coretan-pena/')

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

    context = {
        'kind': kind,
        'breadcrumbs': _breadcrumbs(('CMS', '/cms/'), ('Notifikasi', '/cms/notifications/'), ('Detail Notifikasi', None)),
    }

    if kind == 'payment':
        payment = get_object_or_404(MyPayment, pk=pk)
        if request.method == 'POST' and not payment.is_verified and not payment.is_canceled:
            decision = request.POST.get('decision', '').strip()
            if decision == 'approve':
                payment.is_verified = True
                payment.is_canceled = False
                payment.pemroses = request.user.username
                payment.save()
                messages.add_message(request, messages.SUCCESS, f'Pembayaran {payment.payment} berhasil disetujui.')
            elif decision == 'reject':
                payment.is_verified = False
                payment.is_canceled = True
                payment.pemroses = request.user.username
                payment.save()
                messages.add_message(request, messages.SUCCESS, f'Pembayaran {payment.payment} berhasil ditolak.')
            return HttpResponseRedirect('/cms/notifications/')
        context['payment'] = payment
        context['payment_details'] = MyPaymentDetail.objects.select_related('book').filter(payment=payment)

    elif kind == 'donation':
        donation = get_object_or_404(MyDonation, pk=pk)
        if request.method == 'POST' and not donation.is_verified and not donation.is_canceled:
            decision = request.POST.get('decision', '').strip()
            if decision == 'approve':
                donation.is_verified = True
                donation.is_canceled = False
                donation.pemroses = request.user.username
                donation.save()
                messages.add_message(request, messages.SUCCESS, f'Donasi dari {donation.initial} berhasil disetujui.')
            elif decision == 'reject':
                donation.is_verified = False
                donation.is_canceled = True
                donation.pemroses = request.user.username
                donation.save()
                messages.add_message(request, messages.SUCCESS, f'Donasi dari {donation.initial} berhasil ditolak.')
            return HttpResponseRedirect('/cms/notifications/')
        context['donation'] = donation

    elif kind == 'coretan_moderation':
        blog = get_object_or_404(Blogs, pk=pk, tipe='Coretan Pena')
        if request.method == 'POST':
            blog.is_active = not blog.is_active
            blog.save()
            status_text = 'diaktifkan' if blog.is_active else 'dinonaktifkan'
            messages.add_message(request, messages.SUCCESS, f'Coretan pena "{blog.header}" berhasil {status_text}.')
            return HttpResponseRedirect('/cms/notifications/')
        context['blog'] = blog

    elif kind == 'review_sahabat':
        review = get_object_or_404(PageReview, pk=pk)
        if request.method == 'POST':
            review.is_active = not review.is_active
            review.save()
            status_text = 'ditampilkan' if review.is_active else 'disembunyikan'
            messages.add_message(request, messages.SUCCESS, f'Review sahabat berhasil {status_text}.')
            return HttpResponseRedirect('/cms/notifications/')
        context['review_sahabat'] = review

    elif kind == 'review_buku':
        review = get_object_or_404(BookReview, pk=pk)
        if request.method == 'POST':
            review.is_published = not review.is_published
            review.save()
            status_text = 'dipublikasikan' if review.is_published else 'disembunyikan'
            messages.add_message(request, messages.SUCCESS, f'Review buku berhasil {status_text}.')
            return HttpResponseRedirect('/cms/notifications/')
        context['review_buku'] = review

    elif kind == 'coretan_status':
        blog = get_object_or_404(Blogs, pk=pk, tipe='Coretan Pena', author=request.user)
        context['blog'] = blog

    else:
        messages.add_message(request, messages.SUCCESS, 'Notifikasi tidak dikenali.')
        return HttpResponseRedirect('/cms/notifications/')

    return render(request, 'cms/notification_detail.html', context)
