from django.urls import path
from .views import mainPage, bacaBuku,logoutUser,resetPassword, verifyLinkLupaPassword
from .views import addWishList, delWishList, test123,allBookView, addCartList, cartView, delCartList, changeCartStatus
from .views import listInboxMessage,sinopsisBuku,allBlogsView,detailBlog,paymentProcess
from .views import bacaBukuKoleksi, allKoleksiView,profileView,profileUpdate,listPayment,gantiPasswordPage
from .views import pencarianInfo, tentangKami, melakukanDonasi

urlpatterns = [
    path('', mainPage,name="main_page"),
    path('book/', bacaBuku,name="baca_buku"),
    path('book/p/<str:id>/', bacaBukuKoleksi,name="baca_buku_koleksi"),
    path('book/k/', allKoleksiView,name="semua_buku_koleksi"),
    path('book/<str:id>/', sinopsisBuku,name="sinopsis_buku"),
    path('logout/',logoutUser,name='logout_user'),
    path('forgot/',resetPassword,name="reset_password"),
    path('forgot/<str:id>/',verifyLinkLupaPassword,name="verify_link_lupa_password"),
    path('wish/add/<str:id>/',addWishList,name="add_wish_list"),
    path('wish/del/<str:id>/',delWishList,name="del_wish_list"),
    path('test/',test123,name='test123'),
    path('books/',allBookView,name="all_book_view"),
    path('cart/add/<str:id>/',addCartList,name="add_cart_list"),
    path('cart/',cartView,name="cart_view"),
    path('cart/del/<str:id>/',delCartList,name="del_cart_list"),
    path('cart/change/<str:id>/',changeCartStatus,name="change_cart_status"),
    path('inbox/',listInboxMessage,name='list_inbox_message'),
    path('blogs/',allBlogsView,name="all_blogs_view"),
    path('blogs/<str:id>/',detailBlog,name="detail_blog"),
    path('buy/', paymentProcess,name="payment_process"),
    path('profile/',profileView,name="profile_view"),
    path('profile/p/',gantiPasswordPage,name="ganti_password_page"),
    path('profile/e/',profileUpdate,name="profile_update"),
    path('buy/list/', listPayment,name="list_payment"),
    path('search/', pencarianInfo,name="pencarian_info"),
    path('about/', tentangKami,name="tentang_kami"),
    path('donasi/', melakukanDonasi,name="melakukan_donasi"),
]
