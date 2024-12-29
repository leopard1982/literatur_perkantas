from django.http import HttpResponseRedirect
from django.shortcuts import render, HttpResponse
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from .models import PageReview,Books,FeaturedBook, Category, OnSaleBook, Pengumuman, Instagram, RegisterEmail
from .models import UserBook, LupaPassword
from django.db.models import Avg,Q
import datetime
from django.contrib import messages
from django.contrib.auth.models import User
import uuid
from django.contrib.auth import authenticate,login,logout
from django.contrib.sessions.models import Session
import random

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

def verifyLinkRegistrasi(request,id):
    try:
        registeremail = RegisterEmail.objects.get(Q(id=id) & Q(is_used=False))
        if(registeremail.expired.timestamp()>datetime.datetime.now().timestamp()):
            try:
                password = request.GET['p']
            except Exception as ex:
                print(ex)
                password = str(uuid.uuid4())
            try:
                print(password)
                user = User.objects.create(
                    username=registeremail.email,
                    password=password,
                    email=registeremail.email
                )
                user.set_password(password)
                user.save()
                registeremail.is_used=True
                registeremail.save()
                
                #send email again
                subject = "Initial Email dan Password"
                message = f"\n Hallo Ka selamat untuk email {registeremail.email} sudah terdaftar di Litanas Perkantas Nasional!. \n \n Terlampir Username dan Password yang bisa kaka pakai: \n \n \n ****** \n Username (email): {registeremail.email} \n Password: {password} \n ****** \n \n \n Terima kasih dan Tuhan memberkati! \n \n \n Salam, \n \n \n Literatur Perkantas Nasional \n \n \n Tautan Literatur Nasional Perkantas: https://literatur.pythonanywhere.com/"
                from_email = settings.DEFAULT_FROM_EMAIL
                try:
                    send_mail(
                    subject,
                    message,
                    from_email,
                    [f"{registeremail.email}"],
                    fail_silently=False
                    )
                    messages.add_message(request,messages.SUCCESS,f"Hallo Ka, silakan cek email Anda untuk konfirmasi.")
                except Exception as ex:
                    messages.add_message(request,messages.SUCCESS,"maaf, proses registrasi terhenti.. silakan coba lagi nanti...")
                    print(ex)
                messages.add_message(request,messages.SUCCESS,f"Selamat Kaka sudah terdaftar! Silakan cek email untuk melihat username dan password kaka yah....")
            except Exception as ex:
                print(ex)
                messages.add_message(request,messages.SUCCESS,'Email sudah terdaftar, Apabila kaka lupa password boleh klik link lupa password yah...')
        else:
            messages.add_message(request,messages.SUCCESS,'Link Konfirmasi Sudah Kadaluarsa... Silakan Registrasi Ulang Kembali yah...')
    except Exception as ex:
        print(ex)
        messages.add_message(request,messages.SUCCESS,f"Selamat Kaka sudah terdaftar! Silakan cek email untuk melihat username dan password kaka yah....")
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
    else:
        userbook = None

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
                
            
            registeremail = RegisterEmail.objects.create(email=email)
            print(type(registeremail.email))
            id_register = RegisterEmail.objects.all().filter(email=email).order_by('-created_at')[0]
            subject = "Konfirmasi Registrasi"
            message = f"Hallo Ka, untuk melanjutkan registrasi email: {registeremail.email}, silakan klik link ini untuk konfirmasi: https://literatur.pythonanywhere.com/reg/{id_register.id}/?p={password1} yah... Tuhan Memberkati!"
            from_email = settings.DEFAULT_FROM_EMAIL
            try:
                send_mail(
                subject,
                message,
                from_email,
                [f"{request.POST['username_register']}"],
                fail_silently=False
                )
                messages.add_message(request,messages.SUCCESS,f"Hallo Ka, silakan cek email Anda untuk konfirmasi.")
            except Exception as ex:
                messages.add_message(request,messages.SUCCESS,"maaf, proses registrasi terhenti.. silakan coba lagi nanti...")
                print(ex)

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
        'userbook':userbook
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

