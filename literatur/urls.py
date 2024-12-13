from django.urls import path
from .views import mainPage, bacaBuku

urlpatterns = [
    path('', mainPage,name="main_page"),
    path('book/', bacaBuku,name="baca_buku"),
]
