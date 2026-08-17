from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Blogs, Books


class StaticViewSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return [
            "main_page",
            "baca_buku",
            "semua_buku_koleksi",
            "all_book_view",
            "all_blogs_view",
            "tentang_kami",
            "melakukan_donasi",
        ]

    def location(self, item):
        return reverse(item)


class BookSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Books.objects.order_by("-updated_at").only("id", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("sinopsis_buku", args=[obj.id])


class BlogSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return Blogs.objects.filter(is_active=True).order_by("-updated_at").only("id", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("detail_blog", args=[obj.id])
