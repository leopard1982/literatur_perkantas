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


@override_settings(MEDIA_ROOT=MEDIA, ALLOWED_HOSTS=['testserver'], MOBILE_LOGIN_RECAPTCHA=False)
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
            from PIL import Image
            for n in (1, 6):
                Image.new('RGB', (1200, 1600), 'white').save(os.path.join(d, f'{n}.jpg'))
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

    def test_cover_thumbnail(self):
        r = self.client.get(f'/api/v1/books/{self.paid.id}/cover/?w=240')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'image/jpeg')
        self.assertIn('public', r['Cache-Control'])
        from PIL import Image
        import io
        self.assertEqual(Image.open(io.BytesIO(b''.join(r.streaming_content))).width, 240)
        # non-whitelisted width falls back to 480, bad ids 404
        r = self.client.get(f'/api/v1/books/{self.paid.id}/cover/?w=99999')
        self.assertEqual(Image.open(io.BytesIO(b''.join(r.streaming_content))).width, 480)
        self.assertEqual(self.client.get('/api/v1/books/nope/cover/').status_code, 404)

    def test_media_image_allowlist_and_etag(self):
        from PIL import Image
        os.makedirs(os.path.join(MEDIA, 'blogs'), exist_ok=True)
        Image.new('RGBA', (1600, 900), (255, 0, 0, 128)).save(os.path.join(MEDIA, 'blogs', 'a.png'))
        r = self.client.get('/api/v1/img/?p=blogs/a.png&w=240')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'image/jpeg')
        r2 = self.client.get('/api/v1/img/?p=blogs/a.png&w=240', HTTP_IF_NONE_MATCH=r['ETag'])
        self.assertEqual(r2.status_code, 304)
        # sensitive / traversal paths are refused
        for bad in ('bukti_bayar/x.jpg', '../db.sqlite3', 'blogs/../bukti_bayar/x.jpg', '/etc/passwd', 'profile/a.jpg'):
            self.assertEqual(self.client.get('/api/v1/img/', {'p': bad}).status_code, 404, bad)

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


@override_settings(MEDIA_ROOT=MEDIA, ALLOWED_HOSTS=['testserver'], MOBILE_LOGIN_RECAPTCHA=False)
class BookActiveDeleteTests(TestCase):
    """CMS toggle (aktif/nonaktif) + delete-only-if-never-bought, and what 'nonaktif' means."""

    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser('root', 'r@example.com', 'x-12345678')
        self.buyer = User.objects.create_user('buyer', 'b@example.com', 'rahasia-123')
        UserDetail.objects.create(user=self.buyer, nama_lengkap='Buyer')
        cat = Category.objects.create(id=1, nama='Rohani', gambar='gambar_category/x.jpg')
        self.fresh = Books.objects.create(judul='Belum Dibeli', pengarang='A', kategori=cat, price=1000, halaman=10, is_update_info=True)
        self.sold = Books.objects.create(judul='Sudah Dibeli', pengarang='B', kategori=cat, price=1000, halaman=10, is_update_info=True)
        pay = MyPayment.objects.create(payment='INV9', user=self.buyer)
        UserBook.objects.create(id_book=self.sold, id_user=self.buyer, payment=pay)
        # leftovers on disk for the fresh book
        d = os.path.join(MEDIA, 'extract', 'pdf_full', str(self.fresh.id))
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, '1.jpg'), 'wb').write(b'x')
        self.client.force_login(self.admin)

    def test_toggle_requires_post_and_login(self):
        url = f'/cms/books/{self.fresh.id}/toggle/'
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post(url).status_code, 302)  # -> login
        self.fresh.refresh_from_db()
        self.assertTrue(self.fresh.is_active)

    def test_toggle_flips_state(self):
        url = f'/cms/books/{self.fresh.id}/toggle/'
        self.client.post(url)
        self.fresh.refresh_from_db()
        self.assertFalse(self.fresh.is_active)
        self.client.post(url)
        self.fresh.refresh_from_db()
        self.assertTrue(self.fresh.is_active)

    def test_delete_never_bought_removes_book_and_files(self):
        r = self.client.post(f'/cms/books/{self.fresh.id}/delete/')
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Books.objects.filter(id=self.fresh.id).exists())
        self.assertFalse(os.path.exists(os.path.join(MEDIA, 'extract', 'pdf_full', str(self.fresh.id))))

    def test_delete_refused_when_bought(self):
        self.client.post(f'/cms/books/{self.sold.id}/delete/')
        self.assertTrue(Books.objects.filter(id=self.sold.id).exists())

    def test_delete_requires_post(self):
        self.assertEqual(self.client.get(f'/cms/books/{self.fresh.id}/delete/').status_code, 405)
        self.assertTrue(Books.objects.filter(id=self.fresh.id).exists())

    def test_dashboard_shows_controls(self):
        html = self.client.get('/cms/books/').content.decode()
        self.assertIn(f'/cms/books/{self.fresh.id}/delete/', html)       # deletable
        self.assertNotIn(f'/cms/books/{self.sold.id}/delete/', html)     # bought -> disabled button only
        self.assertIn(f'/cms/books/{self.sold.id}/toggle/', html)

    def test_inactive_is_hidden_from_catalog_but_owner_still_reads(self):
        self.client.logout()
        Books.objects.filter(pk=self.fresh.pk).update(is_active=False)
        Books.objects.filter(pk=self.sold.pk).update(is_active=False)
        # public API: gone from lists, home, search and detail
        listing = self.client.get('/api/v1/books/').json()['results']
        self.assertEqual(listing, [])
        home = self.client.get('/api/v1/home/').json()
        self.assertEqual(home['new_books'] + home['best_seller'] + home['free_books'], [])
        self.assertEqual(self.client.get(f'/api/v1/books/{self.fresh.id}/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/books/{self.sold.id}/').status_code, 404)  # anonymous
        # web: catalogue, search, synopsis and preview reader hide it
        self.assertNotIn('Belum Dibeli', self.client.get('/books/').content.decode())
        self.assertEqual(self.client.get(f'/book/?id={self.fresh.id}').status_code, 302)
        # owner: still in collection, detail and reader
        tok = post(self.client, '/api/v1/auth/login/', {'username': 'buyer', 'password': 'rahasia-123'}).json()['access_token']
        h = {'HTTP_AUTHORIZATION': 'Bearer ' + tok}
        self.assertEqual([b['judul'] for b in self.client.get('/api/v1/me/collection/', **h).json()['results']], ['Sudah Dibeli'])
        self.assertEqual(self.client.get(f'/api/v1/books/{self.sold.id}/', **h).status_code, 200)
        self.assertEqual(self.client.get(f'/api/v1/books/{self.fresh.id}/', **h).status_code, 404)  # not owned
        # cannot be bought
        r = post(self.client, f'/api/v1/cart/{self.fresh.id}/', {}, **h)
        self.assertEqual((r.status_code, r.json()['error']['code']), (409, 'inactive'))
        self.client.force_login(self.buyer)
        self.client.get(f'/cart/add/{self.fresh.id}/', HTTP_REFERER='/')
        from literatur.models import MyCart
        self.assertFalse(MyCart.objects.filter(user=self.buyer, book=self.fresh).exists())
        self.assertEqual(self.client.get(f'/book/p/{self.sold.id}/').status_code, 200)

    def test_active_book_is_listed(self):
        ids = [b['id'] for b in self.client.get('/api/v1/books/').json()['results']]
        self.assertIn(str(self.fresh.id), ids)


@override_settings(ALLOWED_HOSTS=['testserver'], MOBILE_LOGIN_RECAPTCHA=True)
class LoginRecaptchaTests(TestCase):
    def setUp(self):
        cache.clear()
        u = User.objects.create_user('budi', 'budi@example.com', 'rahasia-123')
        UserDetail.objects.create(user=u, nama_lengkap='Budi')

    def test_login_rejected_without_or_with_bad_token(self):
        from unittest import mock
        r = post(self.client, '/api/v1/auth/login/', {'username': 'budi', 'password': 'rahasia-123'})
        self.assertEqual((r.status_code, r.json()['error']['code']), (400, 'captcha_failed'))
        with mock.patch('mobile_api.views.urllib.request.urlopen', side_effect=OSError):
            r = post(self.client, '/api/v1/auth/login/', {'username': 'budi', 'password': 'rahasia-123', 'recaptcha_token': 'x'})
        self.assertEqual(r.status_code, 400)

    def test_login_ok_with_valid_token(self):
        from unittest import mock
        fake = mock.MagicMock()
        fake.__enter__.return_value.read.return_value = b'{"success":true,"score":0.9,"action":"login"}'
        with mock.patch('mobile_api.views.urllib.request.urlopen', return_value=fake):
            r = post(self.client, '/api/v1/auth/login/', {'username': 'budi', 'password': 'rahasia-123', 'recaptcha_token': 'tok'})
        self.assertEqual(r.status_code, 200)

    def test_page_served(self):
        r = self.client.get('/api/v1/auth/recaptcha/')
        self.assertContains(r, 'grecaptcha.execute')


@override_settings(ALLOWED_HOSTS=['testserver'])
class AnnouncementsTests(TestCase):
    def test_only_active_listed_publicly(self):
        from literatur.models import MobileBroadcast
        MobileBroadcast.objects.create(jenis='promo', header='Diskon', body='50%')
        MobileBroadcast.objects.create(jenis='pengumuman', header='Off', body='x', is_active=False)
        r = self.client.get('/api/v1/announcements/')
        self.assertEqual([b['header'] for b in r.json()['results']], ['Diskon'])


@override_settings(MEDIA_ROOT=MEDIA, ALLOWED_HOSTS=['testserver'], MOBILE_LOGIN_RECAPTCHA=False)
class ReaderFeatureTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('budi', 'budi@example.com', 'rahasia-123')
        UserDetail.objects.create(user=self.user, nama_lengkap='Budi')
        free = Category.objects.create(id=3, nama='Gratis')
        paid = Category.objects.create(id=1, nama='Rohani')
        self.paid = Books.objects.create(judul='Berbayar', pengarang='A', kategori=paid, price=50000, halaman=20, is_update_info=True)
        self.free = Books.objects.create(judul='Gratis', pengarang='B', kategori=free, halaman=20, is_update_info=True)
        tok = post(self.client, '/api/v1/auth/login/', {'username': 'budi', 'password': 'rahasia-123'}).json()['access_token']
        self.h = {'HTTP_AUTHORIZATION': 'Bearer ' + tok}

    def test_not_owned_paid_book_is_rejected(self):
        r = post(self.client, f'/api/v1/books/{self.paid.id}/bookmarks/', {'page': 1, 'color': 'red'}, **self.h)
        self.assertEqual(r.status_code, 403)
        r = post(self.client, f'/api/v1/books/{self.paid.id}/comments/', {'comment': 'x'}, **self.h)
        self.assertEqual(r.status_code, 403)

    def test_free_book_bookmark_plan_progress_comment(self):
        u = f'/api/v1/books/{self.free.id}/'
        r = post(self.client, u + 'bookmarks/', {'page': 3, 'color': 'blue', 'note': 'penting'}, **self.h)
        self.assertEqual(r.status_code, 201)
        r2 = post(self.client, u + 'bookmarks/', {'page': 3, 'color': 'green', 'note': 'ubah'}, **self.h)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(self.client.get(u + 'bookmarks/', **self.h).json()['results'][0]['color'], 'green')
        self.assertEqual(post(self.client, u + 'bookmarks/', {'page': 99, 'color': 'red'}, **self.h).status_code, 400)
        self.assertEqual(post(self.client, u + 'bookmarks/', {'page': 2, 'color': 'nope'}, **self.h).status_code, 400)
        g = self.client.get('/api/v1/me/bookmarks/', **self.h).json()['results']
        self.assertEqual(g[0]['book']['id'], str(self.free.id))
        self.assertEqual(g[0]['bookmarks'][0]['note'], 'ubah')
        self.assertEqual(self.client.get('/api/v1/me/bookmarks/').status_code, 401)
        self.assertEqual(self.client.delete(f"/api/v1/bookmarks/{r.json()['id']}/", **self.h).status_code, 200)
        self.assertEqual(self.client.put(u + 'progress/', json.dumps({'page': 7}), content_type='application/json', **self.h).status_code, 200)
        self.assertEqual(self.client.get(u + 'progress/', **self.h).json()['page'], 7)
        self.assertEqual(self.client.get(u, **self.h).json()['last_page'], 7)
        import datetime
        t = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
        self.assertEqual(self.client.put(u + 'plan/', json.dumps({'target_date': t}), content_type='application/json', **self.h).json()['plan']['target_date'], t)
        self.assertEqual(self.client.put(u + 'plan/', json.dumps({'target_date': t, 'remind_time': '07:30'}), content_type='application/json', **self.h).json()['plan']['remind_time'], '07:30')
        self.assertEqual(self.client.put(u + 'plan/', json.dumps({'target_date': t, 'remind_time': 'abc'}), content_type='application/json', **self.h).status_code, 400)
        first = self.client.get(u + 'plan/', **self.h).json()['plan']
        self.assertEqual(first['start_page'], 1)
        pl = self.client.get('/api/v1/me/plans/', **self.h).json()['results']
        self.assertEqual((pl[0]['book']['id'], pl[0]['page'], pl[0]['remind_time']), (str(self.free.id), 7, '07:30'))
        self.assertEqual(self.client.put(u + 'plan/', json.dumps({'target_date': '2001-01-01'}), content_type='application/json', **self.h).status_code, 400)
        self.assertEqual(post(self.client, u + 'comments/', {'comment': 'Bagus'}, **self.h).status_code, 201)
        self.assertEqual(self.client.get(u, **self.h).json()['comments'][0]['comment'], 'Bagus')

    @override_settings(MOBILE_LOGIN_RECAPTCHA=True)
    def test_captcha_required(self):
        r = post(self.client, f'/api/v1/books/{self.free.id}/comments/', {'comment': 'x'}, **self.h)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error']['code'], 'captcha_failed')

    def test_review_crud(self):
        self.assertIsNone(self.client.get('/api/v1/me/review/', **self.h).json()['review'])
        r = self.client.put('/api/v1/me/review/', json.dumps({'review': 'Bukunya bagus'}), content_type='application/json', **self.h)
        self.assertEqual(r.json()['review']['review'], 'Bukunya bagus')
        self.client.put('/api/v1/me/review/', json.dumps({'review': 'Diubah'}), content_type='application/json', **self.h)
        self.assertEqual(self.client.get('/api/v1/me/review/', **self.h).json()['review']['review'], 'Diubah')
        self.assertEqual(self.client.put('/api/v1/me/review/', json.dumps({'review': 'x' * 401}), content_type='application/json', **self.h).status_code, 400)
        self.assertIsNone(self.client.delete('/api/v1/me/review/', **self.h).json()['review'])

    @override_settings(MOBILE_LOGIN_RECAPTCHA=True)
    def test_review_requires_captcha(self):
        r = self.client.put('/api/v1/me/review/', json.dumps({'review': 'x'}), content_type='application/json', **self.h)
        self.assertEqual(r.json()['error']['code'], 'captcha_failed')
