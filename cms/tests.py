import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from literatur.models import QrisCode, qris_url

MEDIA = tempfile.mkdtemp()


def png(size=(300, 300)):
    b = io.BytesIO()
    Image.new('RGB', size, 'black').save(b, 'PNG')
    return SimpleUploadedFile('x.png', b.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=MEDIA, ALLOWED_HOSTS=['testserver', 'localhost'])
class QrisSettingsTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.admin = User.objects.create_superuser('boss', 'b@example.com', 'pw-123456')
        self.client.force_login(self.admin)

    def test_only_admin_and_superadmin_roles(self):
        from django.contrib.auth.models import Group
        for role, allowed in (('Keuangan', False), ('Penulis', False), ('Admin', True), ('Superadmin', True)):
            u = User.objects.create_user(f'u-{role}', password='pw-123456')
            u.groups.add(Group.objects.get_or_create(name=role)[0])
            self.client.force_login(u)
            self.assertEqual(self.client.get('/cms/qris/').status_code, 200 if allowed else 302, role)
            r = self.client.post('/cms/qris/', {'action': 'upload', 'tujuan': 'donasi', 'gambar': png()})
            self.assertEqual(QrisCode.objects.filter(pemroses=u.username).exists(), allowed, role)
            if allowed:
                QrisCode.objects.all().delete()

    def up(self, tujuan, f):
        return self.client.post('/cms/qris/', {'action': 'upload', 'tujuan': tujuan, 'gambar': f, 'keterangan': 'uji'})

    def test_requires_cms_login(self):
        self.client.logout()
        self.assertEqual(self.client.get('/cms/qris/').status_code, 302)
        self.assertEqual(self.client.post('/cms/qris/', {'action': 'upload'}).status_code, 302)

    def test_fallback_then_upload_replaces_active_per_purpose(self):
        d = QrisCode.objects.get(tujuan='donasi', is_active=True) if qris_url('donasi') else None
        self.assertEqual((d.keterangan, d.pemroses), ('QRIS bawaan (default)', 'sistem'))  # default seeded from the static file
        self.assertEqual(qris_url('donasi'), d.url)
        self.up('donasi', png())
        a = QrisCode.objects.get(tujuan='donasi', is_active=True)
        self.assertNotEqual(a.pk, d.pk)
        self.assertEqual(qris_url('donasi'), a.url)
        self.assertFalse(QrisCode.objects.filter(tujuan='pembelian').exists())  # purposes are independent
        self.up('donasi', png((400, 400)))
        self.assertEqual(QrisCode.objects.filter(tujuan='donasi', is_active=True).count(), 1)
        self.assertFalse(QrisCode.objects.get(pk=a.pk).is_active)
        # re-activate the old one, and only inactive ones can be deleted
        self.client.post('/cms/qris/', {'action': 'activate', 'id': a.pk})
        self.assertTrue(QrisCode.objects.get(pk=a.pk).is_active)
        self.client.post('/cms/qris/', {'action': 'delete', 'id': a.pk})
        self.assertTrue(QrisCode.objects.filter(pk=a.pk).exists())

    def test_rejects_bad_files(self):
        self.up('donasi', SimpleUploadedFile('x.png', b'<script>alert(1)</script>', content_type='image/png'))
        self.up('donasi', png((50, 50)))
        self.up('hack', png())
        self.assertEqual(QrisCode.objects.count(), 0)  # nothing seeded by a rejected upload

    def test_pages_use_cms_qris(self):
        self.up('donasi', png())
        url = QrisCode.objects.get(tujuan='donasi').url
        self.client.logout()
        r = self.client.get('/donasi/')
        self.assertContains(r, url)

    def test_dashboard_shows_default_for_both_purposes(self):
        r = self.client.get('/cms/qris/')
        self.assertContains(r, '<br>QRIS bawaan (default)', count=2)
        self.assertEqual(QrisCode.objects.filter(is_active=True).count(), 2)


@override_settings(MEDIA_ROOT=MEDIA, ALLOWED_HOSTS=['testserver', 'localhost'])
class RevenueShareTests(TestCase):
    def setUp(self):
        from literatur.models import Books, Category, MyPayment, MyPaymentDetail
        self.User, self.Books, self.MyPayment, self.Detail = User, Books, MyPayment, MyPaymentDetail
        self.admin = User.objects.create_superuser('boss', 'b@example.com', 'pw-123456')
        self.buyer = User.objects.create_user('pembeli', 'p@example.com', 'pw-123456')
        cat = Category.objects.create(id=1, nama='Rohani')
        self.book = Books.objects.create(judul='Buku A', pengarang='Pak A', kategori=cat, price=100000, halaman=10,
                                         persen_penulis=30, persen_litanas=70, is_update_info=True)

    def pay(self, inv, harga=100000):
        buyer = self.User.objects.create_user(f'pembeli-{inv}', f'{inv}@example.com', 'pw-123456')  # one purchase per user+book
        p = self.MyPayment.objects.create(payment=inv, user=buyer, total=harga, bukti='x')
        d = self.Detail.objects.create(payment=p, book=self.book, harga=harga)
        return p, d

    def approve(self, p):
        p.is_verified, p.is_canceled = True, False
        p.save()

    def test_split_is_frozen_at_approval(self):
        p, d = self.pay('INV1', 99999)
        self.approve(p)
        d.refresh_from_db()
        self.assertEqual((d.persen_penulis, d.persen_litanas), (30, 70))
        self.assertEqual(d.bagian_penulis + d.bagian_litanas, d.harga)  # exact, no rounding drift
        self.assertEqual(float(d.bagian_penulis), 29999.7)
        self.book.persen_penulis, self.book.persen_litanas = 50, 50
        self.book.save()
        d.refresh_from_db()
        self.assertEqual(float(d.bagian_penulis), 29999.7)  # old transaction unchanged
        p2, d2 = self.pay('INV2')
        self.approve(p2)
        d2.refresh_from_db()
        self.assertEqual(float(d2.bagian_penulis), 50000)

    def test_pending_has_no_share(self):
        _, d = self.pay('INV3')
        self.assertEqual((d.bagian_penulis, d.bagian_litanas), (0, 0))
        from literatur.models import Books
        b = Books.objects.create(judul='Baru', pengarang='Z', kategori=self.book.kategori, is_update_info=True)
        self.assertEqual((b.persen_penulis, b.persen_litanas), (60, 40))  # default bagi hasil

    def test_book_form_requires_100_percent(self):
        from cms.forms import BookForm
        data = {'judul': 'X', 'pengarang': 'Y', 'isbn': '123', 'kategori': self.book.kategori_id, 'price': 1000, 'halaman': 0,
                'point': 0, 'deskripsi': 'd', 'persen_penulis': '60', 'persen_litanas': '30'}
        f = BookForm(data, instance=self.book)
        self.assertFalse(f.is_valid())
        self.assertIn('100%', str(f.non_field_errors()))
        data['persen_litanas'] = '40'
        f2 = BookForm(data, instance=self.book)
        self.assertTrue(f2.is_valid(), f2.errors.as_json())

    def test_report_and_access(self):
        p, _ = self.pay('INV4')
        self.approve(p)
        self.client.force_login(self.admin)
        r = self.client.get('/cms/bagi-hasil/')
        self.assertContains(r, 'Buku A')
        self.assertContains(r, 'Rp 30,000')
        self.assertEqual(self.client.get('/cms/bagi-hasil/export/').status_code, 200)
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get('/cms/bagi-hasil/').status_code, 302)


@override_settings(MEDIA_ROOT=MEDIA, ALLOWED_HOSTS=['testserver', 'localhost'])
class ReportAccessTests(TestCase):
    URLS = ['/cms/payments/export/', '/cms/payments/report/pdf/', '/cms/donations/export/',
            '/cms/donations/report/pdf/', '/cms/bagi-hasil/', '/cms/bagi-hasil/export/']

    def login_as(self, role):
        from django.contrib.auth.models import Group
        u = User.objects.create_user(f'r-{role}', password='pw-123456')
        if role:
            u.groups.add(Group.objects.get_or_create(name=role)[0])
        self.client.force_login(u)

    def test_reports_only_for_keuangan_admin_superadmin(self):
        for role, allowed in (('Keuangan', True), ('Admin', True), ('Superadmin', True), ('Penulis', False), (None, False)):
            self.login_as(role)
            for url in self.URLS:
                code = self.client.get(url).status_code
                self.assertEqual(code == 200, allowed, f'{role} {url} -> {code}')
                if not allowed:
                    self.assertEqual(code, 302, f'{role} {url}')
        self.client.logout()
        for url in self.URLS:
            self.assertEqual(self.client.get(url).status_code, 302, url)
