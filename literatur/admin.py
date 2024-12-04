from django.contrib import admin
from .models import UserDetail, UserBook, customerBookmark,BookReview,Books
# Register your models here.

# class viewCustomerDb(admin.ModelAdmin):
#     list_display= ('username','id_customer','alias','birthday')

# admin.site.register(customerDb,viewCustomerDb)
# admin.site.register(customerBook)
admin.site.register(customerBookmark)
admin.site.register(UserDetail)
admin.site.register(UserBook)
admin.site.register(BookReview)
admin.site.register(Books)
