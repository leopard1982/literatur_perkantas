from django.urls import path
from .views import mainPage, bacaBuku, verifyLinkRegistrasi,logoutUser,resetPassword, verifyLinkLupaPassword

urlpatterns = [
    path('', mainPage,name="main_page"),
    path('book/', bacaBuku,name="baca_buku"),
    path('reg/<str:id>/',verifyLinkRegistrasi,name="verify_link_registrasi"),
    path('logout/',logoutUser,name='logout_user'),
    path('forgot/',resetPassword,name="reset_password"),
    path('forgot/<str:id>/',verifyLinkLupaPassword,name="verify_link_lupa_password"),
]
