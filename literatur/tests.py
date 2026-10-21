from django.test import TestCase

# Create your tests here.


from django.test import TestCase as _TC


class AdminHiddenTests(_TC):
    def test_admin_is_not_exposed(self):
        for path in ('/admin/', '/admin/login/', '/admin/literatur/books/'):
            self.assertEqual(self.client.get(path, HTTP_HOST='localhost').status_code, 404, path)
