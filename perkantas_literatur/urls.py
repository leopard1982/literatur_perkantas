"""
URL configuration for perkantas_literatur project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os

from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path,include,re_path
from django.views.generic import TemplateView
from django.views.static import serve
from django.conf import settings
from django.shortcuts import redirect,render

from literatur.media_guard import protected_media
from literatur.sitemaps import BlogSitemap, BookSitemap, StaticViewSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'books': BookSitemap,
    'blogs': BlogSitemap,
}

# Django admin is hidden: /admin/ answers 404. Pengelolaan dilakukan lewat /cms/. Bila admin Django
# memang diperlukan, set DJANGO_ADMIN_URL=<path-rahasia> (mis. "kelola-7f3a9c/") dan admin hanya
# tersedia di path itu.
_admin_path = os.getenv('DJANGO_ADMIN_URL', '').strip().strip('/')
admin_urls = [path(_admin_path + '/', admin.site.urls)] if _admin_path and _admin_path != 'admin' else []

urlpatterns = admin_urls + [
    path('cms/', include('cms.urls')),
    path('api/v1/', include('mobile_api.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    path('',include('literatur.urls')),
    re_path(r'^media/(?P<path>.*)$', protected_media),
    re_path(r'^static/(?P<path>.*)$', serve,{'document_root': settings.STATIC_ROOT})
]

handler500 = 'literatur.views.error500'
