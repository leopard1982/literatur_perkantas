import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone

from literatur.models import MyPayment, MyPaymentDetail


def _ensure_superuser(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(f"/cms/login/?next={request.path}")

    if not request.user.is_superuser:
        messages.add_message(request, messages.SUCCESS, 'Area CMS hanya dapat diakses menggunakan akun superuser.')
        return HttpResponseRedirect('/')

    return None


def login_view(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return HttpResponseRedirect('/cms/')

    next_url = request.GET.get('next') or request.POST.get('next') or '/cms/'

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.add_message(request, messages.SUCCESS, 'Username atau password CMS tidak sesuai.')
        elif not user.is_superuser:
            messages.add_message(request, messages.SUCCESS, 'Akun ditemukan, tetapi tidak memiliki akses superuser ke CMS.')
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
    blocked = _ensure_superuser(request)
    if blocked:
        return blocked

    context = {
        'cards': [
            {
                'title': 'Management Buku',
                'subtitle': 'Data master buku, kategori, metadata, dan file konten.',
                'href': '/cms/books/',
                'count_label': 'Modul',
                'count_value': 'Buku',
                'tone': 'earth',
            },
            {
                'title': 'Management Harga',
                'subtitle': 'Harga normal, promo, diskon, dan strategi paket penjualan.',
                'href': '/cms/pricing/',
                'count_label': 'Modul',
                'count_value': 'Harga',
                'tone': 'amber',
            },
            {
                'title': 'Management Payment',
                'subtitle': 'Verifikasi pembayaran, antrean invoice, dan tindak lanjut approval.',
                'href': '/cms/payments/',
                'count_label': 'Pending',
                'count_value': MyPayment.objects.filter(is_verified=False, is_canceled=False).count(),
                'tone': 'clay',
            },
            {
                'title': 'Management Pengguna',
                'subtitle': 'Profil user, kontak, status koleksi, dan aktivitas akun.',
                'href': '/cms/users/',
                'count_label': 'Modul',
                'count_value': 'User',
                'tone': 'forest',
            },
            {
                'title': 'Management Donasi',
                'subtitle': 'Validasi bukti donasi, status verifikasi, dan monitoring donatur.',
                'href': '/cms/donations/',
                'count_label': 'Modul',
                'count_value': 'Donasi',
                'tone': 'plum',
            },
            {
                'title': 'Management Konten',
                'subtitle': 'Blog, banner, pengumuman, dan elemen konten landing page.',
                'href': '/cms/content/',
                'count_label': 'Modul',
                'count_value': 'Konten',
                'tone': 'navy',
            },
            {
                'title': 'Laporan & Audit',
                'subtitle': 'Ringkasan transaksi, log pemroses, dan area audit operasional.',
                'href': '/cms/reports/',
                'count_label': 'Modul',
                'count_value': 'Laporan',
                'tone': 'charcoal',
            },
        ],
        'summary': {
            'pending': MyPayment.objects.filter(is_verified=False, is_canceled=False).count(),
            'approved': MyPayment.objects.filter(is_verified=True).count(),
            'rejected': MyPayment.objects.filter(is_verified=False, is_canceled=True).count(),
        }
    }
    return render(request, 'cms/dashboard.html', context)


def module_placeholder(request, title, description, bullets):
    blocked = _ensure_superuser(request)
    if blocked:
        return blocked

    context = {
        'title': title,
        'description': description,
        'bullets': bullets,
    }
    return render(request, 'cms/module_placeholder.html', context)


def books_dashboard(request):
    return module_placeholder(
        request,
        'Management Buku',
        'Area ini disiapkan untuk pengelolaan katalog, metadata, kategori, preview, dan file PDF buku.',
        [
            'Tambah dan edit data buku beserta pengarang, ISBN, dan kategori.',
            'Atur upload PDF, preview, dan status best seller.',
            'Kelola hubungan buku dengan promo, featured section, dan koleksi premium.',
        ],
    )


def pricing_dashboard(request):
    return module_placeholder(
        request,
        'Management Harga',
        'Area ini disiapkan untuk mengelola harga reguler, promo, diskon, dan aturan penawaran buku.',
        [
            'Atur harga dasar buku dan harga promo aktif.',
            'Kelola diskon berdasarkan periode kampanye.',
            'Siapkan validasi harga agar sinkron dengan invoice payment.',
        ],
    )


def users_dashboard(request):
    return module_placeholder(
        request,
        'Management Pengguna',
        'Area ini disiapkan untuk melihat profil pengguna, kontak, koleksi buku, dan status akun.',
        [
            'Lihat data user dan profil detail seperti WhatsApp, pekerjaan, dan alamat.',
            'Pantau jumlah buku yang sudah aktif di koleksi user.',
            'Siapkan tindakan admin untuk reset akses atau tindak lanjut akun bermasalah.',
        ],
    )


def donations_dashboard(request):
    return module_placeholder(
        request,
        'Management Donasi',
        'Area ini disiapkan untuk memverifikasi donasi, memantau bukti transfer, dan mengelola komunikasi donatur.',
        [
            'Verifikasi bukti donasi dan update status donor.',
            'Pantau nominal donasi aktif per periode.',
            'Siapkan audit trail pemroses untuk setiap donasi yang disetujui.',
        ],
    )


def content_dashboard(request):
    return module_placeholder(
        request,
        'Management Konten',
        'Area ini disiapkan untuk mengatur banner, blog, pengumuman, dan elemen konten website.',
        [
            'Kelola blog dan status publish konten.',
            'Atur banner iklan, featured content, dan pengumuman utama.',
            'Jaga agar perubahan konten tetap konsisten dengan kebutuhan landing page.',
        ],
    )


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
    blocked = _ensure_superuser(request)
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

    payments = list(payments)
    selected_payment = None

    if selected_invoice:
        for payment in payments:
            if payment.payment == selected_invoice:
                selected_payment = payment
                break

    if selected_payment is None and payments:
        selected_payment = payments[0]

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
        'payments': payments,
        'selected_payment': selected_payment,
        'selected_details': selected_details,
        'current_status': status_filter,
        'current_query': query,
        'stats': stats,
    }
    return render(request, 'cms/payment_dashboard.html', context)
