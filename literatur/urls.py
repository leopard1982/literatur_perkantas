from django.urls import path
from .views import mainPage, bacaBuku,logoutUser,resetPassword, verifyLinkLupaPassword
from .views import addWishList, delWishList, test123,allBookView, addCartList, cartView, delCartList, changeCartStatus

urlpatterns = [
    path('', mainPage,name="main_page"),
    path('book/', bacaBuku,name="baca_buku"),
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
]
