from django.urls import path, re_path

from . import views

urlpatterns = [
    path('home/', views.home),
    path('books/', views.book_list),
    path('books/<str:book_id>/cover/', views.book_cover),
    path('books/<str:book_id>/', views.book_detail),
    path('img/', views.media_image),
    path('blogs/', views.blog_list),
    path('blogs/<str:blog_id>/', views.blog_detail),
    path('auth/login/', views.login),
    path('auth/refresh/', views.refresh),
    path('auth/logout/', views.logout),
    path('auth/logout-all/', views.logout_all),
    path('me/', views.me),
    path('me/collection/', views.collection),
    path('me/inbox/', views.inbox),
    path('me/inbox/<int:msg_id>/', views.inbox_delete),
    path('wishlist/<str:book_id>/', views.wishlist),
    path('cart/<str:book_id>/', views.cart),
    re_path(r'^.*$', views.not_found),
]
