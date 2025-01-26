from django.http import HttpResponseRedirect
from django.shortcuts import render, HttpResponse
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from .models import PageReview,Books,FeaturedBook, Category, OnSaleBook, Pengumuman, Instagram
from .models import UserBook, LupaPassword, MyWishlist, MyCart, inboxMessage, Blogs
from .models import MyPayment
from django.db.models import Avg,Q,Sum
import datetime
from django.contrib import messages
from django.contrib.auth.models import User
import uuid
from django.contrib.auth import authenticate,login,logout
from django.contrib.sessions.models import Session
import random
from django.core.files.storage import default_storage
import os

def resetPassword(request):
    if( request.method == "POST"):
        try:
            email=request.POST['resetEmail']
            user = User.objects.get(email=email)
            lupapassword = LupaPassword()
            lupapassword.email = email
            lupapassword.save()

            #send email again
            subject = "Reset Password"
            message = f"\n Untuk Reset Password silakan klik pada link:. \n \n https://literatur.pythonanywhere.com/forgot/{lupapassword.id}/ \n \n \n Link ini hanya berlaku 1 jam \n \n \n Terima kasih dan Tuhan memberkati! \n \n \n Salam, \n \n \n Literatur Perkantas Nasional \n \n \n Tautan Literatur Nasional Perkantas: https://literatur.pythonanywhere.com/"
            from_email = settings.DEFAULT_FROM_EMAIL
            try:
                send_mail(
                subject,
                message,
                from_email,
                [f"{email}"],
                fail_silently=False
                )
                messages.add_message(request,messages.SUCCESS,f"Hallo Ka, silakan cek email Anda untuk konfirmasi reset password yah...")
            except Exception as ex:
                messages.add_message(request,messages.SUCCESS,"maaf, proses registrasi terhenti.. silakan coba lagi nanti...")
                print(ex)
            return HttpResponseRedirect('/')
        
        except Exception as ex:
            print(ex)
            messages.add_message(request,messages.SUCCESS,f'Email {request.POST["resetEmail"]} belum terdaftar, silakan registrasi terlebih dahulu yah...')
            return HttpResponseRedirect('/')
    else:
        messages.add_message(request,messages.SUCCESS,'Silakan masukkan email yang akan direset. Terima kasih.')
        return HttpResponseRedirect('/')


def verifyLinkLupaPassword(request,id):
    try:
        resetemail = LupaPassword.objects.get(Q(id=id) & Q(is_used=False))
        if(resetemail.expired.timestamp()>datetime.datetime.now().timestamp()):
            try:
                #create password
                password = []
                for pas1 in range(0,10):
                    password.append(chr(97+int(random.random()*27)))
                
                password="".join(password)
                user = User.objects.get(email=resetemail.email)
                user.set_password(password)
                print(password)
                user.save()

                #update resetemail field to expired
                resetemail.is_used=True
                resetemail.save()
                
                #send email again
                subject = "Password Baru"
                message = f"\n Hallo Ka selamat untuk email {resetemail.email} memiliki password baru: {password} \n \n Password bisa kaka ganti. \n \n \n Terima kasih dan Tuhan memberkati! \n \n \n Salam, \n \n \n Literatur Perkantas Nasional \n \n \n Tautan Literatur Nasional Perkantas: https://literatur.pythonanywhere.com/"
                from_email = settings.DEFAULT_FROM_EMAIL
                try:
                    send_mail(
                    subject,
                    message,
                    from_email,
                    [f"{resetemail.email}"],
                    fail_silently=False
                    )
                    messages.add_message(request,messages.SUCCESS,f"Hallo Ka, silakan cek email Anda untuk melihat password baru....")
                    logout(request)
                except Exception as ex:
                    messages.add_message(request,messages.SUCCESS,"maaf, proses registrasi terhenti.. silakan coba lagi nanti...")
                    print(ex)
            except Exception as ex:
                print(ex)
                # messages.add_message(request,messages.SUCCESS,'Email sudah terdaftar, Apabila kaka lupa password boleh klik link lupa password yah...')
        else:
            messages.add_message(request,messages.SUCCESS,'Link Konfirmasi Sudah Kadaluarsa... Silakan Klik Lupa Password Kembali yah...')
    except Exception as ex:
        print(ex)
        messages.add_message(request,messages.SUCCESS,'Link Konfirmasi Sudah Kadaluarsa... Silakan Klik Lupa Password Kembali yah...')
    return HttpResponseRedirect('/')

def logoutUser(request):
    logout(request)
    return HttpResponseRedirect('/')

def mainPage(request):
    #get user id
    try:
        userid= request.GET['u']
    except:
        userid=None

    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        userbook = UserBook.objects.all().filter(id_user=user)
        mywishlist = MyWishlist.objects.all().filter(user=user)
        jml_wishlist=mywishlist.count()
        jml_mycart = MyCart.objects.all().filter(user=user).count()
        inbox_message = inboxMessage.objects.all().filter(user=user)
        jml_inbox_message = inbox_message.count()
    else:
        userbook = None
        mywishlist = None
        jml_inbox_message=0
        jml_wishlist=0
        jml_mycart=0

    blogs = Blogs.objects.all().filter(is_active=True).order_by('-created_at')[:4]

    if request.method=="POST":
        if 'username_register' in request.POST:
            email = request.POST['username_register']
            password1 = request.POST['password_register1']
            password2 = request.POST['password_register2']
            if(password1!=password2):
                messages.add_message(request,messages.SUCCESS,"Password Dan Konfirmasi Harus Sama! Silakan Ulangi Registrasi Kembali...")
                return HttpResponseRedirect('/')
            try:
                reg=User.objects.get(email=email)
                messages.add_message(request,messages.SUCCESS,"Email sudah terdaftar, silakan login ya kaka...")
                return HttpResponseRedirect('/')
            except:
                pass
                
            try:
                # print(password)
                user = User.objects.create(
                    username=email,
                    password=password1,
                    email=email
                )
                user.set_password(password1)
                user.save()
                
                #send email again
                subject = "Initial Email dan Password"
                message = f"\n Hallo Ka selamat untuk email {email} sudah terdaftar di Litanas Perkantas Nasional!. \n \n Terlampir Username dan Password yang bisa kaka pakai: \n \n \n ****** \n Username (email): {email} \n Password: {password1} \n ****** \n \n \n Terima kasih dan Tuhan memberkati! \n \n \n Salam, \n \n \n Literatur Perkantas Nasional \n \n \n Tautan Literatur Nasional Perkantas: https://literatur.pythonanywhere.com/"
                from_email = settings.DEFAULT_FROM_EMAIL
                try:
                    send_mail(
                    subject,
                    message,
                    from_email,
                    [f"{email}"],
                    fail_silently=False
                    )
                    messages.add_message(request,messages.SUCCESS,f"Selamat Kaka sudah terdaftar! Silakan cek email untuk melihat username dan password kaka yah....")
                except Exception as ex:
                    messages.add_message(request,messages.SUCCESS,"maaf, proses registrasi terhenti.. silakan coba lagi nanti...")
                    print(ex)
                
            except Exception as ex:
                print(ex)
                messages.add_message(request,messages.SUCCESS,'Email sudah terdaftar, Apabila kaka lupa password boleh klik link lupa password yah...')
            return HttpResponseRedirect('/')

        if 'username_login' in request.POST:
            username = request.POST['username_login']
            password = request.POST['password_login']
            user = authenticate(username=username,password=password)
            if(user):
                sessionUser = Session.objects.all()
                #delete aktif session yang ada
                # for ses in sessionUser:
                #         #cek apakah user id sudah pernah login
                #         #jika pernah login hapus semua sesionnya
                #         user_id = int(ses.get_decoded().get('_auth_user_id'))
                #         try:
                #             user_logged_id = int(request.user.id)
                #         except:
                #             user_logged_id=0

                #         if(user_id == user_logged_id):
                #             ses.delete()
                #             ses.save()
                #buat session baru
                login(request,user)
                messages.add_message(request,messages.SUCCESS,f'Hallo, selamat datang {user.username}!')
            else:
                messages.add_message(request,messages.SUCCESS,"Username atau Password tidak sesuai, mohon ulangi login lagi yah...")
            
        return HttpResponseRedirect('/')

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
        'free_book':free_book,
        'userbook':userbook,
        'mywishlist':mywishlist,
        'jumlahwishlist':jml_wishlist,
        'jml_mycart':jml_mycart,
        'jml_inbox_message':jml_inbox_message,
        'blogs':blogs
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
    
    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        mywishlist = MyWishlist.objects.all().filter(user=user)
        jml_wishlist=mywishlist.count()
        inbox_message = inboxMessage.objects.all().filter(user=user)
        jml_inbox_message = inbox_message.count()
        mycart = MyCart.objects.all().filter(user=user)
        jml_mycart = mycart.count()
    else:
        mywishlist = None
        jml_wishlist=0
        jml_inbox_message=0
        mycart=None
        jml_mycart=0

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
        'max_page':max_page,
        'mywishlist':mywishlist,
        'jumlahwishlist':jml_wishlist,
        'jml_inbox_message':jml_inbox_message,
        'jml_mycart':jml_mycart,

    }
    return render(request,'landing/baca-buku.html',context)

def addWishList(request,id):
    if request.user.is_authenticated:
        user = User.objects.get(username=request.user.username)
        try:
            book = Books.objects.get(id=id)
            try:
                userbook = UserBook.objects.get(Q(id_user=user) & Q(id_book=book))
                messages.add_message(request,messages.SUCCESS,"Buku sudah kaka beli, tidak bisa masuk ke wishlist yah... kaka bisa lihat di Koleksiku...")
            except:
                try:
                    mywishlist = MyWishlist()
                    mywishlist.user=user
                    mywishlist.book = book
                    mywishlist.save()
                except Exception as ex:
                    print(ex)
                messages.add_message(request,messages.SUCCESS,'Buku Berhasil ditambahkan dalam wishlist kamu..')
        except:
            messages.add_message(request,messages.SUCCESS,'Buku Tidak diketemukan... Buku gagal ditambahkan ke wishlist kamu...')
    else:
        messages.add_message(request,messages.SUCCESS,'Silakan Login terlebih dahulu untuk bisa menambahkan buku di wishlist...')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def delWishList(request,id):
    if request.user.is_authenticated:
        user = User.objects.get(username=request.user.username)
        try:
            book = Books.objects.get(id=id)
            print(book)
            print(id)
            try:
                MyWishlist.objects.get(Q(book=book) & Q(user=user)).delete()
            except Exception as ex:
                print(ex)
            messages.add_message(request,messages.SUCCESS,'Buku Berhasil dihapus dari wishlist kamu..')
        except:
            messages.add_message(request,messages.SUCCESS,'Buku Tidak diketemukan... Buku gagal dihapus dari wishlist kamu...')
    else:
        messages.add_message(request,messages.SUCCESS,'Silakan Login terlebih dahulu untuk bisa menghapus buku di  wishlist...')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def test123(request):
    try:
        if request.GET['q']!="":
            return HttpResponse(f"Isiannya: {request.GET['q']}")
        else:
            return HttpResponse("Belum Ada Query Params")
    except:
        return HttpResponse("Initial")

def allBookView(request):
    try:
        kategori=request.GET['k']
        if int(kategori)>3 and int(kategori)<10:
            kategori=0
    except Exception as ex:
        kategori=0
        print(ex)

    print(kategori)
    category = Category.objects.all()
    if(kategori==0):
        kategori_buku = Category.objects.all()
    else:
        try:
            kategori_buku = Category.objects.get(id=int(kategori))
        except Exception as ex:
            kategori_buku = Category.objects.all()
    try:
        print(kategori)
        if(int(kategori)==10):
            books = Books.objects.all().filter(is_best_seller=True)
        elif(int(kategori)==11):
            books = Books.objects.all().order_by('-created_at')
        else:
            books = Books.objects.all().filter(kategori=kategori_buku)
    except Exception as ex:
        print(ex)
        books = Books.objects.all()
    
    jumlah_promo = OnSaleBook.objects.all().filter(is_active=True).count()

    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        mywishlist = MyWishlist.objects.all().filter(user=user)
        jml_wishlist=mywishlist.count()
        jml_mycart = MyCart.objects.all().filter(user=user).count()
        inbox_message = inboxMessage.objects.all().filter(user=user)
        jml_inbox_message = inbox_message.count()
    else:
        mywishlist = None
        jml_wishlist=0
        jml_mycart=0
        jml_inbox_message=0

    try:
        pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
    except:
        pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

    context = {
        'category':category,
        'books':books,
        'mywishlist':mywishlist,
        'jumlahwishlist':jml_wishlist,
        'kategori':int(kategori),
        'jumlah_promo':jumlah_promo,
        'pengumuman':pengumuman,
        'jml_mycart':jml_mycart,
        'jml_inbox_message':jml_inbox_message
    }
    return render(request,'landing/all-book.html',context)

def addCartList(request,id):
    if request.user.is_authenticated:
        user = User.objects.get(username=request.user.username)
        try:
            book = Books.objects.get(id=id)
            try:
                try:
                    userbook = UserBook.objects.get(Q(id_user=user) & Q(id_book=book))
                    messages.add_message(request,messages.SUCCESS,f"Kaka sudah pernah membeli buku {book.judul} ini. Silakan cek kembali di Koleksiku yah...")
                except:
                    try:
                        MyWishlist.objects.all().filter(Q(book=book) & Q(user=user)).delete()
                        mycart = MyCart()
                        mycart.user=user
                        mycart.book=book
                        mycart.is_checked=False
                        mycart.save()
                        messages.add_message(request,messages.SUCCESS,"Buku berhasil ditambahkan ke keranjang..")
                    except Exception as ex:
                        print(ex)
                        messages.add_message(request,messages.SUCCESS,'Buku berhasil ditambahkan ke keranjang..')
            except Exception as ex:
                print(ex)
                messages.add_message(request,messages.SUCCESS,"Ups.. ada masalah di server, silakan ulangi lagi kembali...")
        except:
            messages.add_message(request,messages.SUCCESS,"Buku tidak diketemukan...")
    else:
        pass
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))    

def cartView(request):
    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        mywishlist = MyWishlist.objects.all().filter(user=user)
        jml_wishlist=mywishlist.count()
        jml_mycart = MyCart.objects.all().filter(user=user).count()
        jml_dibeli = MyCart.objects.all().filter(Q(user=user) & Q(is_checked=True)).count()
        mycart = MyCart.objects.all().filter(user=user)
        inbox_message = inboxMessage.objects.all().filter(user=user)
        jml_inbox_message = inbox_message.count()
        total_payment = 0
        for cart in mycart.filter(is_checked=True):
            try:
                onsalebook = OnSaleBook.objects.get(Q(book=cart.book) & Q(is_active=True))
                total_payment+=int(onsalebook.nett_price)
            except:
                total_payment+=int(cart.book.price)

        try:
            pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
        except:
            pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

        context = {
            'mywishlist':mywishlist,
            'jumlahwishlist':jml_wishlist,
            'pengumuman':pengumuman,
            'jml_mycart':jml_mycart,
            'mycart':mycart,
            'total_payment':total_payment,
            'jml_dibeli':jml_dibeli,
            'jml_inbox_message':jml_inbox_message

        }
        return render(request,'landing/daftar_cart.html',context)
    else:
        return HttpResponseRedirect('/')

    

def delCartList(request,id):
    if request.user.is_authenticated:
        user = User.objects.get(username=request.user.username)
        try:
            book = Books.objects.get(id=id)
            try:
                MyCart.objects.all().filter(Q(user=user) & Q(book=book)).delete()
                messages.add_message(request,messages.SUCCESS,"Buku berhasil dihapus dari keranjang...")
            except:
                messages.add_message(request,messages.SUCCESS,"Buku gagal dihapus dari keranjang...")    
        except:
            messages.add_message(request,messages.SUCCESS,"Buku tidak diketemukan...")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER')) 
    else:
        return HttpResponseRedirect('/')
       

def changeCartStatus(request,id):
    if request.user.is_authenticated:
        user = User.objects.get(username=request.user.username)
        try:
            book = Books.objects.get(id=id)
            try:
                mycart = MyCart.objects.all().get(Q(user=user) & Q(book=book))
                if mycart.is_checked==True:
                    mycart.is_checked=False
                else:
                    mycart.is_checked=True
                mycart.save()
            except:
                messages.add_message(request,messages.SUCCESS,"Buku gagal dihapus dari keranjang...")    
        except:
            messages.add_message(request,messages.SUCCESS,"Buku tidak diketemukan...")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
        return HttpResponseRedirect('/')
    
def listInboxMessage(request):
    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        mywishlist = MyWishlist.objects.all().filter(user=user)
        jml_wishlist=mywishlist.count()
        jml_mycart = MyCart.objects.all().filter(user=user).count()
        jml_dibeli = MyCart.objects.all().filter(Q(user=user) & Q(is_checked=True)).count()
        mycart = MyCart.objects.all().filter(user=user)
        inbox_message = inboxMessage.objects.all().filter(user=user).order_by('-id')
        jml_inbox_message = inbox_message.count()

        try:
            pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
        except:
            pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"
        
        context = {
            'mywishlist':mywishlist,
            'jumlahwishlist':jml_wishlist,
            'pengumuman':pengumuman,
            'jml_mycart':jml_mycart,
            'mycart':mycart,
            'jml_dibeli':jml_dibeli,
            'jml_inbox_message':jml_inbox_message,
            'inbox_message':inbox_message
        }
        return render(request,'landing/list-inbox.html',context)
    else:
        return HttpResponseRedirect('/')
    
def sinopsisBuku(request,id):
    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        mywishlist = MyWishlist.objects.all().filter(user=user)
        jml_wishlist=mywishlist.count()
        jml_mycart = MyCart.objects.all().filter(user=user).count()
        jml_dibeli = MyCart.objects.all().filter(Q(user=user) & Q(is_checked=True)).count()
        mycart = MyCart.objects.all().filter(user=user)
        inbox_message = inboxMessage.objects.all().filter(user=user).order_by('-id')
        jml_inbox_message = inbox_message.count()
    else:
        mywishlist=None
        jml_wishlist=0
        jml_mycart=0
        mycart=None
        jml_dibeli=None
        jml_inbox_message=0
        inbox_message=None

    try:
            pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
    except:
            pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

    try:
        book = Books.objects.get(id=id)
        context = {
            'mywishlist':mywishlist,
            'jumlahwishlist':jml_wishlist,
            'pengumuman':pengumuman,
            'jml_mycart':jml_mycart,
            'mycart':mycart,
            'jml_dibeli':jml_dibeli,
            'jml_inbox_message':jml_inbox_message,
            'inbox_message':inbox_message,
            'book':book
        }
        return render(request,'landing/sinopsis.html',context)
    except:
        messages.add_message(request,messages.SUCCESS,"Maaf sinopsis dari buku yang kaka dari tidak diketemukan...")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        
    
def allBlogsView(request):
    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        mywishlist = MyWishlist.objects.all().filter(user=user)
        jml_wishlist=mywishlist.count()
        jml_mycart = MyCart.objects.all().filter(user=user).count()
        inbox_message = inboxMessage.objects.all().filter(user=user)
        jml_inbox_message = inbox_message.count()
    else:
        mywishlist = None
        jml_wishlist=0
        jml_mycart=0
        jml_inbox_message=0

    blogs = Blogs.objects.all().filter(is_active=True).order_by('-created_at')

    try:
        pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
    except:
        pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

    context = {
        'mywishlist':mywishlist,
        'jumlahwishlist':jml_wishlist,
        'pengumuman':pengumuman,
        'jml_mycart':jml_mycart,
        'jml_inbox_message':jml_inbox_message,
        'blogs':blogs
    }
    return render(request,'landing/all-blogs.html',context)

def detailBlog(request,id):
    try:
        blog = Blogs.objects.get(id=id)
    except:
        messages.add_message(request,messages.success,"Maaf, blogs yang kaka cari tidak ada...")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    
    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        mywishlist = MyWishlist.objects.all().filter(user=user)
        jml_wishlist=mywishlist.count()
        jml_mycart = MyCart.objects.all().filter(user=user).count()
        jml_dibeli = MyCart.objects.all().filter(Q(user=user) & Q(is_checked=True)).count()
        mycart = MyCart.objects.all().filter(user=user)
        inbox_message = inboxMessage.objects.all().filter(user=user).order_by('-id')
        jml_inbox_message = inbox_message.count()
    else:
        mywishlist=None
        jml_wishlist=0
        jml_mycart=0
        mycart=None
        jml_dibeli=None
        jml_inbox_message=0
        inbox_message=None
    
    try:
            pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
    except:
            pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

    prev = request.META.get('HTTP_REFERER')

    context = {
            'mywishlist':mywishlist,
            'jumlahwishlist':jml_wishlist,
            'pengumuman':pengumuman,
            'jml_mycart':jml_mycart,
            'mycart':mycart,
            'jml_dibeli':jml_dibeli,
            'jml_inbox_message':jml_inbox_message,
            'inbox_message':inbox_message,
            'blog':blog,
            'prev':prev
        }
    return render(request,'landing/blog-detail.html',context)

def paymentProcess(request):
    if request.method == "POST":
        if request.user.is_authenticated:
            user = User.objects.get(username=request.user.username)
            x=request.FILES['bukti_bayar']
            filenya = "bukti_bayar/" + str(uuid.uuid4()) + ".jpg"
            default_storage.save(filenya, x)
            id_payment=request.POST['nomor_invoice']
            total_bayar = request.POST['total_bayar']
            nilai_bayar = "".join(total_bayar.split('.00')[0].split(','))
            jumlah_buku = MyCart.objects.all().filter(Q(user=user) & Q(is_checked=True)).count()
            try:
                mypayment = MyPayment()
                mypayment.payment=id_payment
                mypayment.user=user
                mypayment.total=int(nilai_bayar)
                mypayment.bukti=filenya
                mypayment.jumlah_buku=jumlah_buku
                mypayment.save()
                messages.add_message(request,messages.SUCCESS,"Pembayaran kaka telah kami terima, silakan menunggu verifikasi dari kami maksimal 1x24 yah...")

                inboxmessage = inboxMessage()
                inboxmessage.header = "Pembayaran Menunggu Konfirmasi"
                inboxmessage.body = f"Pembayaran untuk nomor invoice {id_payment} telah kami terima, silakan menunggu konfirmasi dari admin kami maksimal 1x24 jam. Tuhan memberkati!!"
                inboxmessage.user=user
                inboxmessage.save()

                MyCart.objects.all().filter(Q(user=user) & Q(is_checked=True)).delete()
                
            except Exception as ex:
                print(ex)
        else:
            messages.add_message(request,messages.SUCCESS,"Silakan Kaka login terlebih dahulu untuk memproses pembayaran...")

        
    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        mywishlist = MyWishlist.objects.all().filter(user=user)
        jml_wishlist=mywishlist.count()
        jml_mycart = MyCart.objects.all().filter(user=user).count()
        jml_dibeli = MyCart.objects.all().filter(Q(user=user) & Q(is_checked=True)).count()
        mycart = MyCart.objects.all().filter(user=user)
        mycart_buy = mycart.filter(is_checked=True)
        jml_mcart_buy = mycart_buy.count()
        inbox_message = inboxMessage.objects.all().filter(user=user).order_by('-id')
        jml_inbox_message = inbox_message.count()

        if(mycart_buy.count()==0) :
            return HttpResponseRedirect("/cart/")
    
        try:
            pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
        except:
            pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

        nomor_invoice = 'ltn'+str(datetime.datetime.now().year) + str(uuid.uuid4())

        total_bayar = 0

        for cart in mycart_buy:
            book = Books.objects.get(id=cart.book.id)
            try:
                onsalebook = OnSaleBook.objects.get(book=book)
                if(onsalebook.is_active==True):
                    total_bayar+=onsalebook.nett_price
                else:
                    total_bayar+=book.price
            except:
                total_bayar+=cart.book.price

        context = {
                'mywishlist':mywishlist,
                'jumlahwishlist':jml_wishlist,
                'pengumuman':pengumuman,
                'jml_mycart':jml_mycart,
                'mycart':mycart,
                'jml_dibeli':jml_dibeli,
                'jml_inbox_message':jml_inbox_message,
                'inbox_message':inbox_message,
                'mycart_buy':mycart_buy,
                'nomor_invoice':nomor_invoice,
                'jml_mycart_buy':jml_mcart_buy,
                'total_bayar':total_bayar,
                'no_rekening':'1234567890',
                'nama_bank':'BCA Cabang Pulo Gadung',
                'nama_pemilik':'Literatur Perkantas Nasional'
            }
        return render(request,'landing/payment.html',context)
    else:
        return HttpResponseRedirect('/cart/')
    
    
    