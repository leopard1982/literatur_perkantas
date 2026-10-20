import json
import os
import tempfile

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings

from literatur.models import Books, Category, MyPayment, UserBook, UserDetail

MEDIA = tempfile.mkdtemp()


def post(client, url, data, **extra):
    return client.post(url, json.dumps(data), content_type='application/json', **extra)


@override_settings(MEDIA_ROOT=MEDIA, ALLOWED_HOSTS=['testserver'])
class ApiSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('budi', 'budi@example.com', 'rahasia-123')
        UserDetail.objects.create(user=self.user, nama_lengkap='Budi Santoso')
        self.other = User.objects.create_user('ani', 'ani@example.com', 'rahasia-456')
        UserDetail.objects.create(user=self.other, nama_lengkap='Ani')
        self.staff = User.objects.create_user('adm', 'a@example.com', 'x-12345678', is_staff=True)
        free = Category.objects.create(id=3, nama='Gratis')
        paid = Category.objects.create(id=1, nama='Rohani')
        self.paid = Books.objects.create(judul='Berbayar', pengarang='A', kategori=paid, price=50000, halaman=20, is_update_info=True)
        self.free = Books.objects.create(judul='Gratis', pengarang='B', kategori=free, halaman=20, is_update_info=True)
        pay = MyPayment.objects.create(payment='INV1', user=self.user, bukti='bukti_bayar/x.jpg')
        UserBook.objects.create(id_book=self.paid, id_user=self.user, payment=pay)
        for book in (self.paid, self.free):
            d = os.path.join(MEDIA, 'extract', 'pdf_full', str(book.id))
            os.makedirs(d, exist_ok=True)
            for n in (1, 6):
                open(os.path.join(d, f'{n}.jpg'), 'wb').write(b'\xff\xd8jpg')
        os.makedirs(os.path.join(MEDIA, 'bukti_bayar'), exist_ok=True)
        open(os.path.join(MEDIA, 'bukti_bayar', 'x.jpg'), 'wb').write(b'x')

    def login(self, username='budi', password='rahasia-123'):
        return post(self.client, '/api/v1/auth/login/', {'username': username, 'password': password})

    # ---- auth
    def test_login_ok_and_tokens_hashed(self):
        r = self.login()
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn('access_token', body)
        from mobile_api.models import ApiSession
        s = ApiSession.objects.get()
        self.assertNotIn(body['access_token'], (s.access_hash, s.refresh_hash))
        self.assertEqual(r['Cache-Control'], 'private, no-store')

    def test_login_generic_error_and_lockout(self):
        a = self.login('budi', 'salah')
        b = self.login('tidak-ada', 'salah')
        self.assertEqual(a.status_code, 401)
        self.assertEqual(a.json(), b.json())
        for _ in range(5):
            self.login('budi', 'salah')
        r = self.login('budi', 'rahasia-123')  # correct password but locked
        self.assertEqual(r.status_code, 429)

    def test_requires_token_and_ignores_session_cookie(self):
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 401)
        self.client.login(username='budi', password='rahasia-123')  # web session
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 401)
        self.assertEqual(self.client.get('/api/v1/me/', HTTP_AUTHORIZATION='Bearer nope').status_code, 401)

    def test_me_and_logout(self):
        tok = self.login().json()['access_token']
        h = {'HTTP_AUTHORIZATION': 'Bearer ' + tok}
        self.assertEqual(self.client.get('/api/v1/me/', **h).json()['nama_lengkap'], 'Budi Santoso')
        self.assertEqual(post(self.client, '/api/v1/auth/logout/', {}, **h).status_code, 200)
        self.assertEqual(self.client.get('/api/v1/me/', **h).status_code, 401)

    def test_refresh_rotation_and_reuse_detection(self):
        t = self.login().json()
        r1 = post(self.client, '/api/v1/auth/refresh/', {'refresh_token': t['refresh_token']})
        self.assertEqual(r1.status_code, 200)
        new = r1.json()
        self.assertNotEqual(new['refresh_token'], t['refresh_token'])
        # old access token is dead after rotation
        self.assertEqual(self.client.get('/api/v1/me/', HTTP_AUTHORIZATION='Bearer ' + t['access_token']).status_code, 401)
        # replaying the old refresh token = theft -> whole session revoked
        self.assertEqual(post(self.client, '/api/v1/auth/refresh/', {'refresh_token': t['refresh_token']}).status_code, 401)
        self.assertEqual(post(self.client, '/api/v1/auth/refresh/', {'refresh_token': new['refresh_token']}).status_code, 401)

    def test_password_change_invalidates_tokens(self):
        tok = self.login().json()['access_token']
        self.user.set_password('baru-789')
        self.user.save()
        self.assertEqual(self.client.get('/api/v1/me/', HTTP_AUTHORIZATION='Bearer ' + tok).status_code, 401)

    def test_input_validation(self):
        self.assertEqual(self.client.post('/api/v1/auth/login/', 'username=a', content_type='text/plain').status_code, 415)
        self.assertEqual(post(self.client, '/api/v1/auth/login/', {'username': ['x'], 'password': 1}).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/auth/login/', '{bad', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.get('/api/v1/auth/login/').status_code, 405)

    # ---- public data
    def test_public_endpoints_and_no_pii(self):
        r = self.client.get('/api/v1/home/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('public', r['Cache-Control'])
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        self.assertNotIn('budi@example.com', r.content.decode())
        d = self.client.get(f'/api/v1/books/{self.paid.id}/').json()
        self.assertNotIn('pdf_full', d)
        self.assertEqual(self.client.get('/api/v1/books/not-a-uuid/').status_code, 404)
        self.assertEqual(self.client.get('/api/v1/nope/').json()['error']['code'], 'not_found')

    def test_book_list_injection_params(self):
        r = self.client.get("/api/v1/books/?k=abc&page=-5&limit=99999&q=' OR 1=1 --")
        self.assertEqual(r.status_code, 200)

    def test_inbox_isolated_per_user(self):
        from literatur.models import inboxMessage
        mine = inboxMessage(user=self.user, header='Halo', body='b')
        mine.save()  # model's save() writes twice, so create() would collide on the pk
        theirs = inboxMessage(user=self.other, header='Rahasia', body='x')
        theirs.save()
        h = {'HTTP_AUTHORIZATION': 'Bearer ' + self.login().json()['access_token']}
        res = self.client.get('/api/v1/me/inbox/', **h).json()['results']
        self.assertEqual([m['id'] for m in res], [mine.id])
        self.client.delete(f'/api/v1/me/inbox/{theirs.id}/', **h)
        self.assertTrue(inboxMessage.objects.filter(id=theirs.id).exists())
        self.client.delete(f'/api/v1/me/inbox/{mine.id}/', **h)
        self.assertFalse(inboxMessage.objects.filter(id=mine.id).exists())

    def test_cart_rules(self):
        h = {'HTTP_AUTHORIZATION': 'Bearer ' + self.login('ani', 'rahasia-456').json()['access_token']}
        self.assertEqual(post(self.client, f'/api/v1/cart/{self.free.id}/', {}, **h).status_code, 409)
        self.assertEqual(post(self.client, f'/api/v1/cart/{self.paid.id}/', {}, **h).json()['in_cart'], True)

    # ---- media guard
    def media(self, book, n, user=None):
        self.client.logout()
        if user:
            self.client.force_login(user)
        return self.client.get(f'/media/extract/pdf_full/{book.id}/{n}.jpg')

    def test_paid_pages_gated(self):
        self.assertEqual(self.media(self.paid, 1).status_code, 200)            # cover public
        self.assertEqual(self.media(self.paid, 6).status_code, 403)            # anonymous
        self.assertEqual(self.media(self.paid, 6, self.other).status_code, 403)  # not owner
        self.assertEqual(self.media(self.paid, 6, self.user).status_code, 200)   # owner
        self.assertEqual(self.media(self.paid, 6, self.staff).status_code, 200)
        self.assertEqual(self.media(self.free, 6).status_code, 200)            # free book

    def test_paid_pages_with_bearer(self):
        tok = self.login().json()['access_token']
        r = self.client.get(f'/media/extract/pdf_full/{self.paid.id}/6.jpg', HTTP_AUTHORIZATION='Bearer ' + tok)
        self.assertEqual(r.status_code, 200)

    def test_receipts_gated_and_traversal(self):
        self.client.logout()
        self.assertEqual(self.client.get('/media/bukti_bayar/x.jpg').status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get('/media/bukti_bayar/x.jpg').status_code, 403)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/media/bukti_bayar/x.jpg').status_code, 200)
        self.assertEqual(self.client.get('/media/donation/a.jpg').status_code, 403)
        self.assertEqual(self.client.get('/media/extract/../../db.sqlite3').status_code, 404)
        self.assertEqual(self.client.get('/media/extract/pdf_full/').status_code, 404)

    def test_test123_is_plain_text(self):
        r = self.client.get('/test/?q=<script>alert(1)</script>')
        self.assertTrue(r['Content-Type'].startswith('text/plain'))
