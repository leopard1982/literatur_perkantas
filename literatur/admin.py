from django.contrib import admin
from .models import UserDetail, UserBook, customerBookmark,BookReview,Books,BannerIklan,Blogs
from .models import PageReview, Category, FeaturedBook,OnSaleBook, Pengumuman, Instagram, inboxMessage
from .models import MyPayment, MyPaymentDetail
# class viewCustomerDb(admin.ModelAdmin):
#     list_display= ('username','id_customer','alias','birthday')

# admin.site.register(customerDb,viewCustomerDb)
admin.site.register(Category)
admin.site.register(customerBookmark)
admin.site.register(UserDetail)
admin.site.register(UserBook)
admin.site.register(BookReview)
admin.site.register(Books)
admin.site.register(PageReview)
admin.site.register(FeaturedBook)
admin.site.register(OnSaleBook)
admin.site.register(Pengumuman)
admin.site.register(Instagram)
admin.site.register(BannerIklan)
admin.site.register(inboxMessage)
admin.site.register(Blogs)
admin.site.register(MyPaymentDetail)
admin.site.register(MyPayment)