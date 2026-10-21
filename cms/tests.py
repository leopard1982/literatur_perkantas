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
