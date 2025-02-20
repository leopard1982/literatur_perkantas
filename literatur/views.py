from django.http import HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render, HttpResponse
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from .models import PageReview,Books,FeaturedBook, Category, OnSaleBook, Pengumuman, Instagram
from .models import UserBook, LupaPassword, MyWishlist, MyCart, inboxMessage, Blogs, UserDetail
from .models import MyPayment, MyPaymentDetail, MyDonation
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
from django.core.paginator import Paginator
from .forms import FormUpdateProfile
from django.template import loader
from .forms import FormMyDonation
# test untuk delete session user
from django.contrib.sessions.models import Session

def bulanTeks(bulan):
    if bulan==1:
        return "Januari"
    elif bulan==2:
        return "Februari"
    elif bulan==3:
        return "Maret"
    elif bulan==4:
        return "April"
    elif bulan==5:
        return "Mei"
    elif bulan==6:
        return "Juni"
    elif bulan==7:
        return "Juli"
    elif bulan==8:
        return "Agustus"
    elif bulan==9:
        return "September"
    elif bulan==10:
        return "Oktober"
    elif bulan==11:
        return "November"
    elif bulan==12:
        return "Desember"
    
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
            message = f"\nUntuk Reset Password silakan klik pada link:. \n\nhttps://literatur.pythonanywhere.com/forgot/{lupapassword.id}/ \n\n\nLink ini hanya berlaku 1 jam \n\n\nTerima kasih dan Tuhan memberkati! \n\n\nSalam, \n\n\nLiteratur Perkantas Nasional \n\n\nTautan Literatur Nasional Perkantas: https://literatur.pythonanywhere.com/"
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
                user.save()


                #update resetemail field to expired
                resetemail.is_used=True
                resetemail.save()
                
                #send email again
                subject = "Password Baru"
                message = f"\nHallo Ka selamat untuk email {resetemail.email} memiliki password baru: {password} \n\nPassword bisa kaka ganti sesuai keinginan kaka setelah berhasil login. \n\n\nTerima kasih dan Tuhan memberkati! \n\n\nSalam, \n\n\nLiteratur Perkantas Nasional \n\n\nTautan Literatur Nasional Perkantas: https://literatur.pythonanywhere.com/"
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

                # buat pesan inbox
                # kirimkan pesan notifikasi inbox
                inbox = inboxMessage()
                inbox.header="Reset Password Berhasil"
                inbox.body = f"Reset Password ka {user.userdetail.nama_lengkap} berhasil pada {datetime.datetime.now()}. Untuk detail password baru bisa dilihat pada email yang terdaftar. Terima kasih."
                inbox.user=user
                inbox.save()

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

    
    # x=request.session.items()
    # print(x)
    # print(request.user.)

    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        userbook = UserBook.objects.all().filter(id_user=user).order_by('-id')
        jml_userbook=userbook.count()
        userbook=userbook[:4]
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
        jml_userbook=0

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

                 # tambahkan userdetail untuk nama lengkap saja
                userdetail = UserDetail()
                userdetail.user=user
                userdetail.nama_lengkap=user.username
                userdetail.save()
                
                #send email again
                subject = "Initial Email dan Password"
                message = f"\nHallo Ka, selamat untuk email {email} sudah terdaftar di Litanas Perkantas Nasional!. \n\nTerlampir Username dan Password yang bisa kaka pakai: \n\n\n******\nUsername: {email}\nPassword: {password1} \n******\n\nMohon Username dan Password disimpan dan jangan diberikan kepada pihak manapun karena bersifat rahasia.\n\n\nTerima kasih dan Tuhan memberkati! \n\n\nSalam, \n\n\nLiteratur Perkantas Nasional \n\n\nTautan Literatur Nasional Perkantas: https://literatur.pythonanywhere.com/"
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
                # dapatkan semua session dengan user id yang sudah login
                x=Session.objects.all()
                for xx in x:
                    try:
                        # simpan data session di dalam penampung user_id
                        # dan di decoded untuk mendapatkan user id nya
                        user_id = xx.get_decoded()['_auth_user_id']
                        # tipe data user_id adalah str, diubah dulu ke int
                        user_id = int(user_id)
                        # dibandingkan apakah user_id sama dengan id user yang akan login
                        user_id_login = user.id
                        # dicek apakah ada disession untuk login user tersebut
                        if user_id == user_id_login:
                            # jika ada hapus semua sessionnya
                            Session.objects.all().filter(session_key=xx).delete()
                    except Exception as ex:
                        print(ex)
                # dan login
                login(request,user)
                messages.add_message(request,messages.SUCCESS,f'Hallo, selamat datang {user.userdetail.nama_lengkap}!')
            else:
                messages.add_message(request,messages.SUCCESS,"Username atau Password tidak sesuai, mohon ulangi login lagi yah...")
            
        return HttpResponseRedirect('/')

    page_review = PageReview.objects.all().filter(is_active=True).order_by('-updated_at')

    featured_book = FeaturedBook.objects.all().filter(Q(is_active=True) and Q(start_date__lte=datetime.datetime.now().date()) and Q(end_date__gte=datetime.datetime.now().date())).order_by('-updated_at')[:4]
    category = Category.objects.all()
    OnSaleBook.objects.all().filter(end_date__lt=datetime.datetime.now()).delete()
    #id category=3 adalah freebook
    books_best_seller = Books.objects.all().filter(Q(is_best_seller=True) & Q(kategori__in=category.exclude(id=3))).order_by('-updated_at')[:6]
    books = Books.objects.all().order_by('-updated_at')[:4]
    jml_on_sale = OnSaleBook.objects.all().count()
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
        'blogs':blogs,
        'jml_userbook':jml_userbook,
        'jml_on_sale':jml_on_sale,
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


    page = Paginator(books,per_page=8)
    range_page = page.page_range
    
    try:
            halaman = page.page(h)
    except:
            h=1
            halaman = page.page(1)

    if(int(h)>1):
            prev_page=int(h)-1
    else:
            prev_page=1
        
    if(int(h)<page.num_pages):
            next_page=int(h)+1
    else:
            next_page=h

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
        'jml_inbox_message':jml_inbox_message,
        'prev_page':prev_page,
        'next_page':next_page,
        'range_page':range_page,
        'halaman':halaman,
        'current':int(h)
    }
    return render(request,'landing/all-book.html',context)

def addCartList(request,id):
    if request.user.is_authenticated:
        user = User.objects.get(username=request.user.username)
        try:
            book = Books.objects.get(id=id)
            try:
                try:
                    # cek apakah buku tersebut sudah ada di dalam koleksi?
                    userbook = UserBook.objects.get(Q(id_user=user) & Q(id_book=book))
                    messages.add_message(request,messages.SUCCESS,f"Kaka sudah pernah membeli buku {book.judul} ini. Silakan cek kembali di Koleksiku yah...")
                except:
                    # ternyata buku belum ada di koleksi, kita cek apakah sudah ada di dalam payment dengan status
                    # masih proses? jika di temukan status is_waiting=True
                    is_waiting=False
                    mypayment = MyPayment.objects.all().filter(Q(user=user) & Q(is_verified=False) & Q(is_canceled=False))
                    for pay in mypayment:
                        mypaymentdetail = MyPaymentDetail.objects.all().filter(payment=pay)
                        for detail in mypaymentdetail:
                            if detail.book == book:
                                is_waiting=True
                    
                    # pengecekan apakah is_waiting == True
                    if is_waiting:
                        messages.add_message(request,messages.SUCCESS,f"Buku masih dalam proses verifikasi pembelian oleh admin dengan nomor invoice: {detail.payment.payment} jadi tidak bisa masuk keranjang.")
                    else:
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
            h=int(request.GET['h'])
        except:
            h=1

        page = Paginator(inbox_message,per_page=10)
        range_page = page.page_range
    
        try:
            halaman = page.page(h)
        except:
            h=1
            halaman = page.page(1)

        if(int(h)>1):
            prev_page=int(h)-1
        else:
            prev_page=1
        
        if(int(h)<page.num_pages):
            next_page=int(h)+1
        else:
            next_page=h

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
            'inbox_message':inbox_message,
            'prev_page':prev_page,
            'next_page':next_page,
            'range_page':range_page,
            'halaman':halaman,
            'current':int(h)

        }
        return render(request,'landing/list-inbox.html',context)
    else:
        messages.add_message(request,messages.SUCCESS,'Ups.. sepertinya kaka login dari device lain? Silakan kaka login kembali di device ini untuk melanjutkan yah...')
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

    try:
        h=request.GET['h']
    except:
        h=1
    blogs = Blogs.objects.all().filter(is_active=True).order_by('-created_at')
    page = Paginator(blogs,per_page=8)
    range_page = page.page_range
    
    try:
        halaman = page.page(h)
    except:
        h=1
        halaman = page.page(1)

    if(int(h)>1):
        prev_page=int(h)-1
    else:
        prev_page=1
    
    if(int(h)<page.num_pages):
        next_page=int(h)+1
    else:
        next_page=h

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
        'blogs':blogs,
        'prev_page':prev_page,
        'next_page':next_page,
        'range_page':range_page,
        'halaman':halaman,
        'current':int(h)
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
            'prev':prev,
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

                # simpan buku ke paymentdetail
                mycart = MyCart.objects.all().filter(Q(user=user) & Q(is_checked=True))
                for cart in mycart:
                    try:
                        book = Books.objects.get(id=cart.book.id)
                        price=0
                        # pengecekan harga buku
                        # apakah merupakan buku on sale?
                        try:
                            onsalebook = OnSaleBook.objects.get(book=book)
                            # jika onsale maka dikasih harga nett nya
                            price = onsalebook.nett_price
                        except:
                            # jika tidak dikasih harga asli
                            price = book.price
                        paymentdetail = MyPaymentDetail()
                        paymentdetail.payment=mypayment
                        paymentdetail.book=book
                        paymentdetail.harga=int(price)
                        paymentdetail.save()
                    except Exception as ex:
                        print(ex)
                mycart.delete()
                
            except Exception as ex:
                print(ex)
        else:
            messages.add_message(request,messages.SUCCESS,"Ups.. sepertinya kaka baru login di device lain? Silakan Kaka login kembali di browser ini untuk memproses pembayaran...")

        
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
        total_bayar = f"{int(total_bayar)}.00"
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
                'no_rekening':'01230254390',
                'nama_bank':'BCA',
                'nama_pemilik':'PT SULUH  CENDEKIA'
            }
        return render(request,'landing/payment.html',context)
    else:
        messages.add_message(request,messages.SUCCESS,'Ups.. sepertinya kaka login dari device lain? Silakan kaka login kembali di device ini untuk melanjutkan yah...')
        return HttpResponseRedirect('/cart/')
    
    
def bacaBukuKoleksi(request,id):
    try:
        if request.user.is_authenticated:
            user= User.objects.get(username=request.user.username)
            try:
                book = Books.objects.get(id=id)
            except:
                messages.add_message(request,messages.SUCCESS,'Buku yang kaka cari tidak ada...')
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))    
            
            try:
                userbook = UserBook.objects.get(Q(id_book=book) & Q(id_user=user))
            except:
                messages.add_message(request,messages.SUCCESS,'Karena ini buku berbayar, dan kaka belum memiliki di koleksi, kaka hanya bisa melihat preview sampul saja yah...')
                return HttpResponseRedirect(f'/book/?id={book.id}')

            try:
                if request.method=="POST":
                    page = int(request.POST['halaman'])
                else:
                    page=int(request.GET['p'])
                
                if page>book.halaman:
                    page=book.halaman
                userbook.last_page=int(page)
                userbook.save()
            except:
                page=int(userbook.last_page)
                if page==0:
                    page=1
            
            mywishlist = MyWishlist.objects.all().filter(user=user)
            jml_wishlist=mywishlist.count()
            inbox_message = inboxMessage.objects.all().filter(user=user)
            jml_inbox_message = inbox_message.count()
            mycart = MyCart.objects.all().filter(user=user)
            jml_mycart = mycart.count()

            max_page = book.halaman

            if page==1:
                prev=1
            else:
                prev=page-1
            
            next=page+1
            if(next>max_page):
                next=max_page

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
            return render(request,'landing/baca-premium.html',context)
        else:
            messages.add_message(request,messages.SUCCESS,'Ups sepertinya Kaka sudah login di device lain? Untuk bisa membaca buku ini kaka harus login terlebih dahulu dan memiliki buku ini di koleksi kaka..')
            return HttpResponseRedirect("/")
    except Exception as ex:
        print(ex)
        messages.add_message(request,messages.SUCCESS,'Kaka sudah login di device lain, silakan login di device ini untuk bisa melanjutkan baca yah...')
        return HttpResponseRedirect('/')
    

def allKoleksiView(request):
    try:
        h=int(request.GET['h'])
    except:
        h=1

    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        koleksiku = UserBook.objects.all().filter(id_user=user)
        mywishlist = MyWishlist.objects.all().filter(user=user)
        jml_wishlist=mywishlist.count()
        jml_mycart = MyCart.objects.all().filter(user=user).count()
        inbox_message = inboxMessage.objects.all().filter(user=user)
        jml_inbox_message = inbox_message.count()
        jml_koleksiku = koleksiku.count()

        page = Paginator(koleksiku,per_page=8)
        range_page = page.page_range
        
        try:
                halaman = page.page(h)
        except:
                h=1
                halaman = page.page(1)

        if(int(h)>1):
                prev_page=int(h)-1
        else:
                prev_page=1
            
        if(int(h)<page.num_pages):
                next_page=int(h)+1
        else:
                next_page=h

        try:
            pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
        except:
            pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

        context = {
            'koleksiku':koleksiku,
            'mywishlist':mywishlist,
            'jumlahwishlist':jml_wishlist,
            'pengumuman':pengumuman,
            'jml_mycart':jml_mycart,
            'jml_inbox_message':jml_inbox_message,
            'prev_page':prev_page,
            'next_page':next_page,
            'range_page':range_page,
            'halaman':halaman,
            'current':int(h),
            'jml_koleksiku':jml_koleksiku
        }
        return render(request,'landing/all-koleksi.html',context)

    else:
        messages.add_message(request,messages.SUCCESS,'Untuk bisa melihat daftar koleksi, kaka harus login terlebih dahulu yah...')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def profileView(request):
    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        koleksiku = UserBook.objects.all().filter(id_user=user)
        mywishlist = MyWishlist.objects.all().filter(user=user)
        jml_wishlist=mywishlist.count()
        jml_mycart = MyCart.objects.all().filter(user=user).count()
        inbox_message = inboxMessage.objects.all().filter(user=user)
        jml_inbox_message = inbox_message.count()
        try:
            pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
        except:
            pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

        context = {
            'koleksiku':koleksiku,
            'mywishlist':mywishlist,
            'jumlahwishlist':jml_wishlist,
            'pengumuman':pengumuman,
            'jml_mycart':jml_mycart,
            'jml_inbox_message':jml_inbox_message,
        }
        return render(request,'landing/profile.html',context)

    else:
        messages.add_message(request,messages.SUCCESS,'Untuk bisa melihat profile harus login terlebih dahulu kaka...')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def profileUpdate(request):
    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        if request.method == "POST":
            formnya = FormUpdateProfile(data=request.POST,files=request.FILES)
            if formnya.is_valid():
                try:
                    # simpan file foto ke dalam uuid format
                    nama_file = str(uuid.uuid4())
                    #dapatkan extension file
                    extension = request.FILES['photo'].name.split('.')[1]

                    file = request.FILES['photo']
                    filename=default_storage.save(f"{nama_file}.{extension}",file)
                except:
                    file = None
                    filename=""
                updateprofile = UserDetail.objects.get(user=user)
                updateprofile.nama_lengkap = request.POST['nama_lengkap']
                updateprofile.no_whatsapp = request.POST['no_whatsapp']
                updateprofile.pekerjaan = request.POST['pekerjaan']
                updateprofile.alamat = request.POST['alamat']
                
                # jika tanggal lahir ada maka simpan
                if(request.POST['birthday']):
                    tgl = int(request.POST['birthday'].split('-')[2])
                    bulan = int(request.POST['birthday'].split('-')[1])
                    tahun = int(request.POST['birthday'].split('-')[0])
                    updateprofile.birthday = datetime.date(tahun,bulan,tgl)
                
                # jika foto ada simpan
                if(file):
                    updateprofile.photo = filename
                # simpan perubahan
                updateprofile.save()

                # kirim pesan inbox kalau ada perubahan page review
                inbox = inboxMessage()
                inbox.header="Perubahan Profil"
                inbox.body = f"Perubahan Data Profil  untuk {user.userdetail.nama_lengkap} sudah disimpan pada {datetime.datetime.now()}"
                inbox.user=user
                inbox.save()

                messages.add_message(request,messages.SUCCESS,"Info Saya Berhasil Diperbaharui...")

                #sekarang simpan untuk review page
                if(request.POST['review_litanas']):
                    try:
                        # coba untuk dapatkan pagereview
                        pagereview = PageReview.objects.get(user=user)
                        if pagereview.review != request.POST['review_litanas']:
                            pagereview.review=request.POST['review_litanas']
                            pagereview.save()
                            # kirim pesan inbox kalau ada perubahan page review
                            inbox = inboxMessage()
                            inbox.header="Page Review"
                            inbox.body = f"Page Review  untuk {user.userdetail.nama_lengkap} sudah berubah menjadi: {request.POST['review_litanas']} pada {datetime.datetime.now()}"
                            inbox.user=user
                            inbox.save()
                            messages.add_message(request,messages.SUCCESS,"Untuk Page Review Dilakukan Perubahan")
                    except:
                        # kalau tidak ada maka akan buat pagereview baru
                        pagereview = PageReview()
                        pagereview.user=user
                        pagereview.review=request.POST['review_litanas']    
                        pagereview.is_active=True
                        pagereview.save()      
                        messages.add_message(request,messages.SUCCESS,"Untuk Page Review Sudah Bershasil Disimpan dan  Aktif")
                        
                        # kirim pesan inbox kalau ada perubahan page review
                        inbox = inboxMessage()
                        inbox.header="Page Review"
                        inbox.body = f"Page Review  untuk {user.userdetail.nama_lengkap} berhasil disimpan pada {datetime.datetime.now()}. Kaka bisa melihat di bagian Review Sahabat."
                        inbox.user=user
                        inbox.save()
                        messages.add_message(request,messages.SUCCESS,"Info Saya Berhasil Diperbaharui...")
            else:
                messages.add_message(request,messages.SUCCESS,"Info Saya Gagal Diperbaharui...")
            return HttpResponseRedirect('/profile/')

        koleksiku = UserBook.objects.all().filter(id_user=user)
        mywishlist = MyWishlist.objects.all().filter(user=user)
        jml_wishlist=mywishlist.count()
        jml_mycart = MyCart.objects.all().filter(user=user).count()
        inbox_message = inboxMessage.objects.all().filter(user=user)
        jml_inbox_message = inbox_message.count()
        userdetail = UserDetail.objects.get(user=user)
        updateprofile = FormUpdateProfile(instance=userdetail)
        try:
            pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
        except:
            pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

        context = {
            'koleksiku':koleksiku,
            'mywishlist':mywishlist,
            'jumlahwishlist':jml_wishlist,
            'pengumuman':pengumuman,
            'jml_mycart':jml_mycart,
            'jml_inbox_message':jml_inbox_message,
            'updateprofile':updateprofile
        }
        return render(request,'landing/profile_edit.html',context)

    else:
        messages.add_message(request,messages.SUCCESS,'Untuk bisa melihat profile harus login terlebih dahulu kaka...')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def listPayment(request):
    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        mywishlist = MyWishlist.objects.all().filter(user=user)
        jml_wishlist=mywishlist.count()
        jml_mycart = MyCart.objects.all().filter(user=user).count()
        jml_dibeli = MyCart.objects.all().filter(Q(user=user) & Q(is_checked=True)).count()
        mycart = MyCart.objects.all().filter(user=user)
        inbox_message = inboxMessage.objects.all().filter(user=user).order_by('-id')
        jml_inbox_message = inbox_message.count()
        mypayment = MyPayment.objects.all().filter(user=user).order_by('-created_at')
        jml_mypayment = mypayment.count()
        mypaymentdetail = MyPaymentDetail.objects.all().filter(payment__in=mypayment)

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
            'inbox_message':inbox_message,
            'mypayment':mypayment,
            'jml_mypayment':jml_mypayment,
            'mypaymentdetail':mypaymentdetail
        }
        return render(request,'landing/detail-payment.html',context)
    else:
        messages.add_message(request,messages.SUCCESS,'Ups.. sepertinya kaka login dari device lain? Silakan kaka login kembali di device ini untuk melanjutkan yah...')
        return HttpResponseRedirect('/')

def gantiPasswordPage(request):
    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)

        if request.method=="POST":
            password_lama = request.POST['password_lama']
            password_baru = request.POST['password_baru']
            password_konfirmasi = request.POST['password_konfirmasi']

            # cek apakah password lama sama
            cek = user.check_password(password_lama)
            if(cek):
                # apakah password baru dan konfirmasinya sama?
                if password_baru != password_konfirmasi:
                    # jika tidak tampilkan pesan tidak sesuai
                    messages.add_message(request,messages.SUCCESS,'Password Baru dan Konfirmasinya Tidak Sesuai, Mohon ulangi kembali...')
                    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
                else:
                    # jika sama maka diset passwordnya
                    user.set_password(password_baru)
                    # simpan credential baru
                    user.save()
                    # logout dari sistem
                    logout(request)
                    # tampilkan pesan
                    messages.add_message(request,messages.SUCCESS,f'Password Berhasil Diubah! Silakan Kaka login kembali menggunakan password baru... Terima kasih...')

                    # kirimkan pesan notifikasi inbox
                    inbox = inboxMessage()
                    inbox.header="Ganti Password"
                    inbox.body = f"Ganti Password untuk {user.userdetail.nama_lengkap} berhasil pada {datetime.datetime.now()}. Untuk detail password baru bisa dilihat pada email yang terdaftar. Terima kasih."
                    inbox.user=user
                    inbox.save()

                    # kirimkan email
                    #send email again
                    subject = "Penggantian Password Berhasil"
                    message = f"Hallo Ka {user.userdetail.nama_lengkap} selamat untuk password berhasil diubah. \n\n********\nPassword Baru: {password_baru}\n********\n\nHarap password tidak diberikan kepada siapapun karena bersifat rahasia. Terima kasih dan Tuhan memberkati\n\n\nSalam, \n\n\nLiteratur Perkantas Nasional \n\n\nTautan Literatur Nasional Perkantas: https://literatur.pythonanywhere.com/"
                    from_email = settings.DEFAULT_FROM_EMAIL
                    try:
                        send_mail(
                        subject,
                        message,
                        from_email,
                        [f"{user.username}"],
                        fail_silently=False
                        )
                    except Exception as ex:
                        pass
                    return HttpResponseRedirect('/')    
            else:     
                messages.add_message(request,messages.SUCCESS,'Password Lama Tidak Sesuai... silakan ulangi kembali...')
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        koleksiku = UserBook.objects.all().filter(id_user=user)
        mywishlist = MyWishlist.objects.all().filter(user=user)
        jml_wishlist=mywishlist.count()
        jml_mycart = MyCart.objects.all().filter(user=user).count()
        inbox_message = inboxMessage.objects.all().filter(user=user)
        jml_inbox_message = inbox_message.count()
        try:
            pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
        except:
            pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

        context = {
            'koleksiku':koleksiku,
            'mywishlist':mywishlist,
            'jumlahwishlist':jml_wishlist,
            'pengumuman':pengumuman,
            'jml_mycart':jml_mycart,
            'jml_inbox_message':jml_inbox_message,
        }
        return render(request,'landing/change_password.html',context)

    else:
        messages.add_message(request,messages.SUCCESS,'Untuk bisa mengganti password harus login terlebih dahulu kaka...')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def pencarianInfo(request):
    try:
        if request.method=="POST":
            keyword = request.POST['s']

            blog = Blogs.objects.all().filter(Q(header__icontains=keyword) | Q(body__icontains=keyword))
            book = Books.objects.all().filter(Q(judul__icontains=keyword) | Q(deskripsi__icontains=keyword) | Q(sinopsis__icontains=keyword) | Q(pengarang__icontains=keyword))

            jumlah_blog = blog.count()
            jumlah_book = book.count()
        else:
            return HttpResponseRedirect('/')
    except:
        return HttpResponseRedirect('/')
    
    try:
            pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
    except:
            pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        userbook = UserBook.objects.all().filter(id_user=user).order_by('-id')
        jml_userbook=userbook.count()
        userbook=userbook[:4]
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
        jml_userbook=0
    
    context = {
        'userbook':userbook,
        'mywishlist':mywishlist,
        'jumlahwishlist':jml_wishlist,
        'jml_mycart':jml_mycart,
        'jml_inbox_message':jml_inbox_message,
        'jml_userbook':jml_userbook,
        'keyword':keyword,
        'book':book,
        'blog':blog,
        'jumlah_blog':jumlah_blog,
        'jumlah_book':jumlah_book,
        'pengumuman':pengumuman
    }
    return render(request,'landing/search.html',context)

def error500(request):
    t = loader.get_template('404.html')
    response = HttpResponseServerError(t.render())
    response.status_code=500
    return response

def tentangKami(request):
    bulan_donasi_now = datetime.datetime.now().month
    tahun_donasi_now = datetime.datetime.now().year
    data_donasi_now = MyDonation.objects.all().filter(Q(updated_at__month=bulan_donasi_now) & Q(updated_at__year=tahun_donasi_now) & Q(is_verified=True))
    
    # jjka data donasi sudah ada maka dijumlah
    if len(data_donasi_now)>0:
        total_donasi_now = MyDonation.objects.all().filter(Q(updated_at__month=bulan_donasi_now) & Q(updated_at__year=tahun_donasi_now) & Q(is_verified=True)).aggregate(jumlah=Sum('nilai'))
        total_now = total_donasi_now['jumlah']
    else:
        # kalau belum ada data donasi di nolkan
        total_now=0
    bulan_now = bulanTeks(bulan_donasi_now) + f" {str(tahun_donasi_now)}"

    try:
            pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
    except:
            pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        userbook = UserBook.objects.all().filter(id_user=user).order_by('-id')
        jml_userbook=userbook.count()
        userbook=userbook[:4]
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
        jml_userbook=0
    
    context = {
        'userbook':userbook,
        'mywishlist':mywishlist,
        'jumlahwishlist':jml_wishlist,
        'jml_mycart':jml_mycart,
        'jml_inbox_message':jml_inbox_message,
        'jml_userbook':jml_userbook,
        'bulan_now':bulan_now,
        'total_now':total_now,
        'pengumuman':pengumuman
    }
    return render(request,'landing/tentangkami.html',context)

def melakukanDonasi(request):
    if request.method=="POST":
        formmydonation=FormMyDonation(data=request.POST,files=request.FILES)
        if(formmydonation.is_valid()):
            formmydonation.save()
            messages.add_message(request,messages.SUCCESS,f'Terima kasih kaka {request.POST["initial"]} atas donasinya. ')
        else:
            messages.add_message(request,messages.SUCCESS,f'Maaf, ada kesalah sistem. Silakan kaka {request.POST["initial"]} ulangi kembali proses donasinya. Terima kasih.')

    bulan_donasi_now = datetime.datetime.now().month
    tahun_donasi_now = datetime.datetime.now().year
    data_donasi_now = MyDonation.objects.all().filter(Q(updated_at__month=bulan_donasi_now) & Q(updated_at__year=tahun_donasi_now) & Q(is_verified=True))
    
    try:
            pengumuman = Pengumuman.objects.all().order_by('-id')[0].pengumuman
    except:
            pengumuman = "Selamat Datang Di Website Literatur Perkantas Nasional!"

    # jjka data donasi sudah ada maka dijumlah
    if len(data_donasi_now)>0:
        total_donasi_now = MyDonation.objects.all().filter(Q(updated_at__month=bulan_donasi_now) & Q(updated_at__year=tahun_donasi_now) & Q(is_verified=True)).aggregate(jumlah=Sum('nilai'))
        total_now = total_donasi_now['jumlah']
    else:
        # kalau belum ada data donasi di nolkan
        total_now=0
    bulan_now = bulanTeks(bulan_donasi_now) + f" {str(tahun_donasi_now)}"

    formmydonation = FormMyDonation()

    if request.user.is_authenticated:
        user= User.objects.get(username=request.user.username)
        userbook = UserBook.objects.all().filter(id_user=user).order_by('-id')
        jml_userbook=userbook.count()
        userbook=userbook[:4]
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
        jml_userbook=0
    
    context = {
        'userbook':userbook,
        'mywishlist':mywishlist,
        'jumlahwishlist':jml_wishlist,
        'jml_mycart':jml_mycart,
        'jml_inbox_message':jml_inbox_message,
        'jml_userbook':jml_userbook,
        'bulan_now':bulan_now,
        'total_now':total_now,
        'no_rekening':'01230254390',
        'nama_bank':'BCA',
        'nama_pemilik':'PT SULUH  CENDEKIA',
        'form':formmydonation,
        'donatur':data_donasi_now,
        'pengumuman':pengumuman
    }
    return render(request,'landing/form-donasi.html',context)
