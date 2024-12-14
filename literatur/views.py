from django.http import HttpResponseRedirect
from django.shortcuts import render, HttpResponse
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from .models import PageReview,Books,FeaturedBook, Category, OnSaleBook, Pengumuman, Instagram
from django.db.models import Avg,Q
import datetime

# Create your views here.
def mainPage(request):
    #get user id
    try:
        userid= request.GET['u']
    except:
        userid=None
    
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
    try:
        id_buku = request.GET['id']
        book = Books.objects.get(id=id_buku)
    except:
        return HttpResponseRedirect(reverse('main_page'))
    
    try:
        page=int(request.GET['p'])
        
        if int(page)>book.halaman:
            page=book.halaman
        
        if page<1:
            page=1

    except:
        page=1

    if page==1:
        prev=1
    else:
        prev=page-1
    
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
        'page':page
    }
    return render(request,'landing/baca-buku.html',context)