from django.http import HttpResponseRedirect
from django.shortcuts import render, HttpResponse
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from .models import PageReview,Books,FeaturedBook, Category, OnSaleBook, Pengumuman, Instagram
from django.db.models import Avg,Q
import datetime
from django.contrib import messages

# Create your views here.
def mainPage(request):
    #get user id
    try:
        userid= request.GET['u']
    except:
        userid=None

    if request.method=="POST":
        #testmail
        subject = "Login From New Device"
        message = f"Hello {request.POST['username_login']} you are login from new device on {datetime.datetime.now()}"
        from_email = settings.DEFAULT_FROM_EMAIL
        try:
            send_mail(
            subject,
            message,
            from_email,
            [f"{request.POST['username_login']}"]
            )
        except Exception as ex:
            print(ex)
        messages.add_message(request,messages.SUCCESS,f"Hallo {request.POST['username_login']} selamat datang!")
    
    page_review = PageReview.objects.all().filter(is_active=True).order_by('-updated_at')

    featured_book = FeaturedBook.objects.all().filter(Q(is_active=True) and Q(start_date__lte=datetime.datetime.now().date()) and Q(end_date__gte=datetime.datetime.now().date())).order_by('-updated_at')[:4]
    category = Category.objects.all()
    OnSaleBook.objects.all().filter(end_date__lt=datetime.datetime.now()).delete()
    #id category=3 adalah freebook
    books_best_seller = Books.objects.all().filter(Q(is_best_seller=True) & Q(kategori__in=category.exclude(id=3))).order_by('-updated_at')[:4]
    books = Books.objects.all().order_by('-updated_at')[:4]
    books_on_sale = OnSaleBook.objects.all().order_by('-updated_at')[:4]
    
    #category=3 free
    free_book = Books.objects.all().filter(kategori__in=category.filter(id=3))
    print(books_on_sale)
    try:
        pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
    except:
        pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

    instagram = Instagram.objects.all().order_by('-id')[:6]

    # messages.add_message(request,messages.ERROR,"Test")

    context = {
        'page_review':page_review,
        'feature_book':featured_book,
        'category':category,
        'books_best_seller':books_best_seller,
        'books':books,
        'books_on_sale':books_on_sale,
        'pengumuman':pengumuman,
        'instagram':instagram,
        'free_book':free_book
    }

    # send_mail('Subject here Test', 'Here is the message. Test', 'adhy.chandra@live.co.uk', ['adhy.chandra@gmail.com'], fail_silently=False)
    return render(request,'index.html',context)

def bacaBuku(request):
    max_page=5
    try:
        id_buku = request.GET['id']
        book = Books.objects.get(id=id_buku)
        print(book.kategori.id)
        if book.kategori.id == 3:
            max_page = book.halaman
    except:
        return HttpResponseRedirect(reverse('main_page'))
    
    try:
        if request.method=="POST":
            page=int(request.POST['halaman'])
            if(page>max_page):
                page=5
        else:
            page=int(request.GET['p'])
            
            if int(page)>max_page:
                page=max_page
            
            if page<1:
                page=1

    except:
        page=1


    

    if page==1:
        prev=1
    else:
        prev=page-1

    if max_page==5 and page==5:
        messages.add_message(request,messages.SUCCESS,"Maksimal Hanya 5 Halaman Saja, Karena Preview Sample")
    
    next=page+1

    try:
        pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
    except:
        pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

    context = {
        'pengumuman':pengumuman,
        'book':book,
        'next':next,
        'prev':prev,
        'page':page,
        'max_page':max_page
    }
    return render(request,'landing/baca-buku.html',context)