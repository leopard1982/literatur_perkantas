from django.urls import path

from .views import (
    books_dashboard,
    content_dashboard,
    dashboard,
    donations_dashboard,
    login_view,
    logout_view,
    payment_dashboard,
    pricing_dashboard,
    reports_dashboard,
    users_dashboard,
)


urlpatterns = [
    path('login/', login_view, name='cms_login'),
    path('logout/', logout_view, name='cms_logout'),
    path('', dashboard, name='cms_dashboard'),
    path('books/', books_dashboard, name='cms_books_dashboard'),
    path('pricing/', pricing_dashboard, name='cms_pricing_dashboard'),
    path('payments/', payment_dashboard, name='cms_payment_dashboard'),
    path('users/', users_dashboard, name='cms_users_dashboard'),
    path('donations/', donations_dashboard, name='cms_donations_dashboard'),
    path('content/', content_dashboard, name='cms_content_dashboard'),
    path('reports/', reports_dashboard, name='cms_reports_dashboard'),
]
