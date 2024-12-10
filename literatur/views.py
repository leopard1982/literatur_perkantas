from django.http import HttpResponseRedirect
from django.shortcuts import render, HttpResponse
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from .models import PageReview,Books,FeaturedBook, Category, OnSaleBook, Pengumuman
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
    books_best_seller = Books.objects.all().filter(is_best_seller=True).order_by('-updated_at')[:4]
    books = Books.objects.all().order_by('-updated_at')[:4]
    books_on_sale = OnSaleBook.objects.all().filter(Q(is_active=True) and Q(start_date__lte=datetime.datetime.now().date()) and Q(end_date__gte=datetime.datetime.now().date())).order_by('-updated_at')[:4]
    try:
        pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
    except:
        pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"
        
    context = {
        'page_review':page_review,
        'feature_book':featured_book,
        'category':category,
        'books_best_seller':books_best_seller,
        'books':books,
        'books_on_sale':books_on_sale,
        'pengumuman':pengumuman
    }

    # send_mail('Subject here Test', 'Here is the message. Test', 'adhy.chandra@live.co.uk', ['adhy.chandra@gmail.com'], fail_silently=False)
    return render(request,'index.html',context)