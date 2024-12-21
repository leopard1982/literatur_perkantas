from django.urls import path
from .views import mainPage, bacaBuku, verifyLinkRegistrasi

urlpatterns = [
    path('', mainPage,name="main_page"),
    path('book/', bacaBuku,name="baca_buku"),
    path('reg/<str:id>/',verifyLinkRegistrasi,name="verify_link_registrasi")
]
