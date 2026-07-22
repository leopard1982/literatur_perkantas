from django.urls import path

from .views import (
    book_form,
    books_dashboard,
    categories_dashboard,
    category_form,
    content_moderation_dashboard,
    coretan_pena_dashboard,
    coretan_pena_form,
    customers_dashboard,
    dashboard,
    donation_dashboard,
    login_view,
    logout_view,
    notification_detail,
    notifications_dashboard,
    onsale_form,
    payment_dashboard,
    promo_bestseller_dashboard,
    reports_dashboard,
    roles_dashboard,
)


urlpatterns = [
    path('login/', login_view, name='cms_login'),
    path('logout/', logout_view, name='cms_logout'),
    path('', dashboard, name='cms_dashboard'),

    path('payments/', payment_dashboard, name='cms_payment_dashboard'),
    path('donations/', donation_dashboard, name='cms_donation_dashboard'),

    path('books/', books_dashboard, name='cms_books_dashboard'),
    path('books/add/', book_form, name='cms_book_add'),
    path('books/<uuid:book_id>/edit/', book_form, name='cms_book_edit'),

    path('categories/', categories_dashboard, name='cms_categories_dashboard'),
    path('categories/add/', category_form, name='cms_category_add'),
    path('categories/<int:category_id>/edit/', category_form, name='cms_category_edit'),

    path('promo/', promo_bestseller_dashboard, name='cms_promo_bestseller_dashboard'),
    path('promo/add/', onsale_form, name='cms_promo_add'),
    path('promo/<int:promo_id>/edit/', onsale_form, name='cms_promo_edit'),

    path('customers/', customers_dashboard, name='cms_customers_dashboard'),

    path('content/', content_moderation_dashboard, name='cms_content_moderation_dashboard'),

    path('roles/', roles_dashboard, name='cms_roles_dashboard'),

    path('coretan-pena/', coretan_pena_dashboard, name='cms_coretan_pena_dashboard'),
    path('coretan-pena/add/', coretan_pena_form, name='cms_coretan_pena_add'),
    path('coretan-pena/<uuid:blog_id>/edit/', coretan_pena_form, name='cms_coretan_pena_edit'),

    path('notifications/', notifications_dashboard, name='cms_notifications_dashboard'),
    path('notifications/<str:kind>/<str:pk>/', notification_detail, name='cms_notification_detail'),

    path('reports/', reports_dashboard, name='cms_reports_dashboard'),
]
