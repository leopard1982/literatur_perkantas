from django.http import HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render, HttpResponse
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from .models import PageReview,Books,FeaturedBook, Category, OnSaleBook, Pengumuman, Instagram
from .models import UserBook, LupaPassword, MyWishlist, MyCart, inboxMessage, Blogs, UserDetail
from .models import MyPayment, MyPaymentDetail, MyDonation
from .models import BlogComment, BookComment
from django.db.models import Avg,Q,Sum,Prefetch
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

DEFAULT_PENGUMUMAN = "Selamat Datang Di Website Literatur Perkantas Nasional!"


def get_authenticated_user(request):
    if request.user.is_authenticated:
        return request.user
    return None


def get_pengumuman_text():
    return (
        Pengumuman.objects.order_by('-id').values_list('pengumuman', flat=True).first()
        or DEFAULT_PENGUMUMAN
    )


def build_user_view_context(
    user,
    *,
    include_cart=False,
    include_checked_cart=False,
    include_inbox=False,
    include_koleksi=False,
    include_userbook_preview=False,
    include_owned_book_ids=False,
):
    context = {
        'mywishlist': None,
        'jumlahwishlist': 0,
        'jml_mycart': 0,
        'jml_inbox_message': 0,
    }

    if user is None:
        if include_checked_cart:
            context['jml_dibeli'] = 0
        if include_cart:
            context['mycart'] = None
        if include_inbox:
            context['inbox_message'] = None
        if include_koleksi:
            context['koleksiku'] = None
            context['jml_koleksiku'] = 0
        if include_userbook_preview:
            context['userbook'] = None
            context['jml_userbook'] = 0
        if include_owned_book_ids:
            context['owned_book_ids'] = []
        return context

    wishlist_qs = MyWishlist.objects.filter(user=user).select_related(
        'book__kategori', 'book__onsalebook'
    ).order_by('-id')
    inbox_qs = inboxMessage.objects.filter(user=user).order_by('-id')

    context.update({
        'mywishlist': wishlist_qs,
        'jumlahwishlist': wishlist_qs.count(),
        'jml_inbox_message': inbox_qs.count(),
    })

    if include_inbox:
        context['inbox_message'] = inbox_qs

    cart_qs = None
    if include_cart or include_checked_cart:
        cart_qs = MyCart.objects.filter(user=user).select_related(
            'book__kategori', 'book__onsalebook'
        ).order_by('-id')
        context['jml_mycart'] = cart_qs.count()
        if include_cart:
            context['mycart'] = cart_qs
        if include_checked_cart:
            context['jml_dibeli'] = cart_qs.filter(is_checked=True).count()
    else:
        context['jml_mycart'] = MyCart.objects.filter(user=user).count()

    koleksi_qs = None
    if include_koleksi or include_userbook_preview or include_owned_book_ids:
        koleksi_qs = UserBook.objects.filter(id_user=user).select_related(
            'id_book__kategori', 'id_book__onsalebook'
        ).order_by('-id')

    if include_koleksi:
        context['koleksiku'] = koleksi_qs
        context['jml_koleksiku'] = koleksi_qs.count()

    if include_userbook_preview:
        context['userbook'] = koleksi_qs[:4]
        context['jml_userbook'] = koleksi_qs.count()

    if include_owned_book_ids:
        context['owned_book_ids'] = list(
            UserBook.objects.filter(id_user=user).values_list('id_book_id', flat=True)
        )

    return context


def build_pagination_context(page_obj, current_page):
    current_page = int(current_page)
    page_range = list(page_obj.paginator.page_range)

    if current_page > 1:
        prev_page = current_page - 1
    else:
        prev_page = 1

    if current_page < page_obj.paginator.num_pages:
        next_page = current_page + 1
    else:
        next_page = current_page

    return {
        'prev_page': prev_page,
        'next_page': next_page,
        'range_page': page_range,
        'halaman': page_obj,
        'current': current_page,
    }


def can_user_comment_book(user, book):
    if user is None:
        return False
    if book.kategori_id == 3:
        return True
    return UserBook.objects.filter(id_user=user, id_book=book).exists()


def get_comment_page(comment_qs, requested_page):
    paginator = Paginator(comment_qs, per_page=10)
    try:
        return paginator.page(requested_page)
    except Exception:
        return paginator.page(1)


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
    messages.add_message(request,messages.SUCCESS,"Kaka sudah logout.. silakan login untuk bisa membaca buku koleksi...")
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

    user = get_authenticated_user(request)
    user_context = build_user_view_context(
        user,
        include_userbook_preview=True,
        include_owned_book_ids=True,
    )

    blogs = Blogs.objects.filter(is_active=True).select_related('author').order_by('-created_at')[:4]

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

    page_review = PageReview.objects.filter(is_active=True).select_related('user__userdetail').order_by('-updated_at')[:10]

    featured_book = FeaturedBook.objects.filter(Q(is_active=True) and Q(start_date__lte=datetime.datetime.now().date()) and Q(end_date__gte=datetime.datetime.now().date())).select_related('book__kategori').order_by('-updated_at')[:4]
    category = Category.objects.all()
    OnSaleBook.objects.filter(end_date__lt=datetime.datetime.now()).delete()
    #id category=3 adalah freebook
    books_best_seller = (
        Books.objects.filter(Q(is_best_seller=True) & Q(kategori__in=category.exclude(id=3)))
        .select_related('kategori', 'onsalebook')
        .annotate(jumlah_dibeli=Count('userbook', distinct=True))
        .order_by('-updated_at')[:6]
    )
    books = (
        Books.objects.select_related('kategori', 'onsalebook')
        .annotate(jumlah_dibeli=Count('userbook', distinct=True))
        .order_by('-updated_at')[:4]
    )
    jml_on_sale = OnSaleBook.objects.count()
    books_on_sale = (
        OnSaleBook.objects.select_related('book__kategori')
        .annotate(jumlah_dibeli=Count('book__userbook', distinct=True))
        .order_by('-updated_at')[:4]
    )

    #category=3 free
    free_book = (
        Books.objects.filter(kategori__in=category.filter(id=3))
        .select_related('kategori')
        .annotate(jumlah_dibeli=Count('userbook', distinct=True))
        .order_by('-updated_at')[:12]
    )
    print(books_on_sale)
    try:
        pengumuman = get_pengumuman_text()
    except:
        pengumuman = DEFAULT_PENGUMUMAN

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
        'blogs':blogs,
        'jml_on_sale':jml_on_sale,
    }
    context.update(user_context)

    # send_mail('Subject here Test', 'Here is the message. Test', 'adhy.chandra@live.co.uk', ['adhy.chandra@gmail.com'], fail_silently=False)
    return render(request,'index.html',context)

def bacaBuku(request):
    max_page = 5
    try:
        id_buku = request.GET['id']
        book = Books.objects.select_related('kategori').get(id=id_buku)
        if book.kategori.id == 3:
            max_page = book.halaman
    except Exception:
        return HttpResponseRedirect(reverse('main_page'))

    user = get_authenticated_user(request)
    can_comment = can_user_comment_book(user, book)

    if request.method == "POST" and request.POST.get('comment_type') == "book":
        comment_value = request.POST.get('comment', '').strip()
        if user is None:
            messages.add_message(request, messages.SUCCESS, "Silakan login terlebih dahulu untuk menambahkan komentar.")
        elif not can_comment:
            messages.add_message(request, messages.SUCCESS, "Komentar hanya tersedia untuk buku gratis atau buku yang sudah ada di koleksi.")
        elif comment_value == "":
            messages.add_message(request, messages.SUCCESS, "Komentar tidak boleh kosong.")
        else:
            existing_comments = BookComment.objects.filter(book=book, user=user).order_by('-updated_at')
            existing_comment = existing_comments.first()
            if existing_comment:
                existing_comment.comment = comment_value
                existing_comment.is_active = True
                existing_comment.is_publish = True
                existing_comment.save()
                existing_comments.exclude(id=existing_comment.id).delete()
                messages.add_message(request, messages.SUCCESS, "Komentar berhasil diperbarui.")
            else:
                BookComment.objects.create(book=book, user=user, comment=comment_value)
                messages.add_message(request, messages.SUCCESS, "Komentar berhasil ditambahkan.")
        p = request.GET.get('p', '1')
        return HttpResponseRedirect(f"{reverse('baca_buku')}?id={book.id}&p={p}#book-comments")

    user_context = build_user_view_context(user)

    try:
        page = int(request.GET.get('p', 1))
    except Exception:
        page = 1

    if page > max_page:
        page = max_page
    if page < 1:
        page = 1

    prev = page - 1 if page > 1 else 1
    next = page + 1
    if next > max_page:
        next = max_page

    if max_page == 5 and page == 5:
        messages.add_message(request, messages.SUCCESS, "Maksimal Hanya 5 Halaman Saja, Karena Preview Sample")

    comments_qs = BookComment.objects.filter(book=book, is_active=True, is_publish=True).select_related('user__userdetail').order_by('-created_at')
    comment_page = request.GET.get('comment_page', 1)
    comments_page_obj = get_comment_page(comments_qs, comment_page)

    try:
        pengumuman = get_pengumuman_text()
    except Exception:
        pengumuman = DEFAULT_PENGUMUMAN

    context = {
        'pengumuman': pengumuman,
        'book': book,
        'next': next,
        'prev': prev,
        'page': page,
        'max_page': max_page,
        'current_page_image': f"/media/extract/pdf_full/{book.id}/{page}.jpg",
        'prev_page_image': f"/media/extract/pdf_full/{book.id}/{prev}.jpg" if page > 1 else None,
        'next_page_image': f"/media/extract/pdf_full/{book.id}/{next}.jpg" if page < max_page else None,
        'comments_page_obj': comments_page_obj,
        'can_comment_book': can_comment,
        'is_preview_reader': True,
        'book_reader_page_base': f"{reverse('baca_buku')}?id={book.id}&p=",
    }
    context.update(user_context)

    if request.headers.get('HX-Request') == 'true':
        return render(request, 'landing/partials/baca-buku-panel.html', context)

    return render(request, 'landing/baca-buku.html', context)

def addWishList(request,id):
    if request.user.is_authenticated:
        user = get_authenticated_user(request)
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
        user = get_authenticated_user(request)
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
    limit_options = [10, 25, 50, 100]
    try:
        kategori = int(request.GET['k'])
        if kategori > 3 and kategori < 10:
            kategori = 0
    except Exception as ex:
        kategori = 0
        print(ex)

    category = Category.objects.all()
    if kategori == 0:
        kategori_buku = None
    else:
        try:
            kategori_buku = Category.objects.get(id=kategori)
        except Exception as ex:
            kategori_buku = None
    try:
        h = int(request.GET.get('h', 1))
    except (ValueError, TypeError):
        h = 1
    try:
        page_size = int(request.GET.get('limit', 10))
        if page_size not in limit_options:
            page_size = 10
    except (ValueError, TypeError):
        page_size = 10

    base_books = Books.objects.select_related('kategori', 'onsalebook')

    try:
        if kategori == 10:
            books = base_books.filter(is_best_seller=True).order_by('-updated_at')
            tab_title = "Buku Best Seller"
            tab_subtitle = "Judul-judul yang paling banyak dipilih pembaca dan layak masuk daftar baca berikutnya."
        elif kategori == 11:
            books = base_books.order_by('-created_at')
            tab_title = "Buku Terbaru"
            tab_subtitle = "Koleksi yang baru masuk ke katalog, disusun untuk memudahkan Anda menemukan rilisan terkini."
        elif kategori == 12:
            books = base_books.filter(onsalebook__is_active=True).order_by('-onsalebook__updated_at', '-updated_at')
            tab_title = "Buku Promo"
            tab_subtitle = "Penawaran aktif dengan harga terbaik yang sedang tersedia untuk dibawa pulang hari ini."
        elif kategori_buku is not None:
            books = base_books.filter(kategori=kategori_buku).order_by('-updated_at')
            tab_title = kategori_buku.nama
            tab_subtitle = f"Jelajahi pilihan buku dalam kategori {kategori_buku.nama.lower()} yang tersusun lebih rapi dan mudah dipindai."
        else:
            books = base_books.order_by('-updated_at')
            tab_title = "Semua Buku"
            tab_subtitle = "Seluruh koleksi Literatur Perkantas Nasional, dari buku gratis sampai judul premium pilihan."
    except Exception as ex:
        print(ex)
        books = base_books.order_by('-updated_at')
        tab_title = "Semua Buku"
        tab_subtitle = "Seluruh koleksi Literatur Perkantas Nasional, dari buku gratis sampai judul premium pilihan."

    jumlah_promo = OnSaleBook.objects.filter(is_active=True).count()

    user_context = build_user_view_context(
        get_authenticated_user(request),
        include_owned_book_ids=True,
    )


    page = Paginator(books, per_page=page_size)
    range_page = page.page_range
    
    try:
        halaman = page.page(h)
    except:
        h=1
        halaman = page.page(1)

    if page.num_pages <= 5:
        page_numbers = list(page.page_range)
    elif h <= 3:
        page_numbers = [1, 2, 3, None, page.num_pages]
    elif h >= page.num_pages - 2:
        page_numbers = [1, None, page.num_pages - 2, page.num_pages - 1, page.num_pages]
    else:
        page_numbers = [1, None, h - 1, h, h + 1, None, page.num_pages]

    try:
        pengumuman = get_pengumuman_text()
    except:
        pengumuman = DEFAULT_PENGUMUMAN

    context = {
        'category':category,
        'books':books,
        'kategori':kategori,
        'jumlah_promo':jumlah_promo,
        'pengumuman':pengumuman,
        'page_numbers':page_numbers,
        'tab_title':tab_title,
        'tab_subtitle':tab_subtitle,
        'total_books':books.count(),
        'page_size':page_size,
        'limit_options':limit_options,
    }
    context.update(user_context)
    context.update(build_pagination_context(halaman, h))
    return render(request,'landing/all-book.html',context)

def addCartList(request,id):
    if request.user.is_authenticated:
        user = get_authenticated_user(request)
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
                    is_waiting = MyPaymentDetail.objects.filter(
                        payment__user=user,
                        payment__is_verified=False,
                        payment__is_canceled=False,
                        book=book
                    ).exists()

                    # pengecekan apakah is_waiting == True
                    if is_waiting:
                        pending = MyPaymentDetail.objects.filter(
                            payment__user=user,
                            payment__is_verified=False,
                            payment__is_canceled=False,
                            book=book
                        ).select_related('payment').first()
                        invoice = pending.payment.payment if pending else "-"
                        messages.add_message(request,messages.SUCCESS,f"Buku masih dalam proses verifikasi pembelian oleh admin dengan nomor invoice: {invoice} jadi tidak bisa masuk keranjang.")
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
        user_context = build_user_view_context(
            get_authenticated_user(request),
            include_cart=True,
            include_checked_cart=True,
        )
        mycart = user_context['mycart']
        total_payment = 0
        for cart in mycart.filter(is_checked=True):
            try:
                onsalebook = cart.book.onsalebook
                if onsalebook.is_active:
                    total_payment += int(onsalebook.nett_price)
                else:
                    total_payment += int(cart.book.price)
            except OnSaleBook.DoesNotExist:
                total_payment += int(cart.book.price)

        try:
            pengumuman = get_pengumuman_text()
        except:
            pengumuman = DEFAULT_PENGUMUMAN

        context = {
            'pengumuman':pengumuman,
            'total_payment':total_payment,

        }
        context.update(user_context)
        return render(request,'landing/daftar_cart.html',context)
    else:
        return HttpResponseRedirect('/')

    

def delCartList(request,id):
    if request.user.is_authenticated:
        user = get_authenticated_user(request)
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
        user = get_authenticated_user(request)
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
        user_context = build_user_view_context(
            get_authenticated_user(request),
            include_cart=True,
            include_checked_cart=True,
            include_inbox=True,
        )
        inbox_message = user_context['inbox_message']

        try:
            h=int(request.GET['h'])
        except:
            h=1

        page = Paginator(inbox_message,per_page=10)
    
        try:
            halaman = page.page(h)
        except:
            h=1
            halaman = page.page(1)

        try:
            pengumuman = get_pengumuman_text()
        except:
            pengumuman = DEFAULT_PENGUMUMAN
        
        context = {
            'pengumuman':pengumuman,
            'inbox_message':inbox_message,
        }
        context.update(user_context)
        context.update(build_pagination_context(halaman, h))
        return render(request,'landing/list-inbox.html',context)
    else:
        messages.add_message(request,messages.SUCCESS,'Ups.. sepertinya kaka login dari device lain? Silakan kaka login kembali di device ini untuk melanjutkan yah...')
        return HttpResponseRedirect('/')

def deleteInboxMessage(request,id):
    if request.user.is_authenticated:
        if request.method != "POST":
            return HttpResponseRedirect(reverse('list_inbox_message'))

        user = get_authenticated_user(request)
        current_page = request.POST.get('h', '1')

        deleted_count, _ = inboxMessage.objects.filter(id=id, user=user).delete()
        if deleted_count > 0:
            messages.add_message(request, messages.SUCCESS, "Notifikasi berhasil dihapus.")
        else:
            messages.add_message(request, messages.SUCCESS, "Notifikasi tidak ditemukan atau sudah dihapus.")

        return HttpResponseRedirect(f"{reverse('list_inbox_message')}?h={current_page}")
    else:
        messages.add_message(request,messages.SUCCESS,'Ups.. sepertinya kaka login dari device lain? Silakan kaka login kembali di device ini untuk melanjutkan yah...')
        return HttpResponseRedirect('/')


def _safe_next_url(request, fallback_url):
    next_url = request.POST.get('next', '').strip()
    if next_url.startswith('/'):
        return next_url
    return fallback_url


def deleteBlogComment(request, id):
    if request.method != "POST":
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('all_blogs_view')))

    user = get_authenticated_user(request)
    if user is None:
        messages.add_message(request, messages.SUCCESS, "Silakan login terlebih dahulu untuk menghapus komentar.")
        return HttpResponseRedirect('/')

    comment = BlogComment.objects.filter(id=id, user=user).first()
    if comment is None:
        messages.add_message(request, messages.SUCCESS, "Komentar tidak ditemukan atau bukan milik kamu.")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('all_blogs_view')))

    blog_id = comment.blog_id
    comment.delete()
    messages.add_message(request, messages.SUCCESS, "Komentar berhasil dihapus.")
    return HttpResponseRedirect(_safe_next_url(request, f"{reverse('detail_blog', args=[blog_id])}#blog-comments"))


def deleteBookComment(request, id):
    if request.method != "POST":
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('main_page')))

    user = get_authenticated_user(request)
    if user is None:
        messages.add_message(request, messages.SUCCESS, "Silakan login terlebih dahulu untuk menghapus komentar.")
        return HttpResponseRedirect('/')

    comment = BookComment.objects.filter(id=id, user=user).first()
    if comment is None:
        messages.add_message(request, messages.SUCCESS, "Komentar tidak ditemukan atau bukan milik kamu.")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('main_page')))

    book_id = comment.book_id
    comment.delete()
    messages.add_message(request, messages.SUCCESS, "Komentar berhasil dihapus.")
    return HttpResponseRedirect(_safe_next_url(request, f"{reverse('sinopsis_buku', args=[book_id])}#book-comments"))
    
def sinopsisBuku(request,id):
    user = get_authenticated_user(request)
    user_context = build_user_view_context(
        user,
        include_cart=True,
        include_checked_cart=True,
        include_inbox=True,
    )

    try:
            pengumuman = get_pengumuman_text()
    except:
            pengumuman = DEFAULT_PENGUMUMAN

    try:
        book = Books.objects.select_related('kategori', 'onsalebook').get(id=id)
        can_comment = can_user_comment_book(user, book)

        if request.method == "POST" and request.POST.get('comment_type') == "book":
            comment_value = request.POST.get('comment', '').strip()
            if user is None:
                messages.add_message(request, messages.SUCCESS, "Silakan login terlebih dahulu untuk menambahkan komentar.")
            elif not can_comment:
                messages.add_message(request, messages.SUCCESS, "Komentar hanya tersedia untuk buku gratis atau buku yang sudah ada di koleksi.")
            elif comment_value == "":
                messages.add_message(request, messages.SUCCESS, "Komentar tidak boleh kosong.")
            else:
                existing_comments = BookComment.objects.filter(book=book, user=user).order_by('-updated_at')
                existing_comment = existing_comments.first()
                if existing_comment:
                    existing_comment.comment = comment_value
                    existing_comment.is_active = True
                    existing_comment.is_publish = True
                    existing_comment.save()
                    existing_comments.exclude(id=existing_comment.id).delete()
                    messages.add_message(request, messages.SUCCESS, "Komentar berhasil diperbarui.")
                else:
                    BookComment.objects.create(book=book, user=user, comment=comment_value)
                    messages.add_message(request, messages.SUCCESS, "Komentar berhasil ditambahkan.")
            return HttpResponseRedirect(f"{reverse('sinopsis_buku', args=[book.id])}#book-comments")

        comments_qs = BookComment.objects.filter(
            book=book,
            is_active=True,
            is_publish=True,
        ).select_related('user__userdetail').order_by('-created_at')

        context = {
            'pengumuman':pengumuman,
            'book':book,
            'comments_page_obj': get_comment_page(comments_qs, request.GET.get('comment_page', 1)),
            'can_comment_book': can_comment,
        }
        context.update(user_context)
        return render(request,'landing/sinopsis.html',context)
    except:
        messages.add_message(request,messages.SUCCESS,"Maaf sinopsis dari buku yang kaka dari tidak diketemukan...")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        
    
def allBlogsView(request):
    user_context = build_user_view_context(get_authenticated_user(request))

    try:
        h=request.GET['h']
    except:
        h=1
    blogs = Blogs.objects.filter(is_active=True).select_related('author').order_by('-created_at')
    page = Paginator(blogs,per_page=8)
    
    try:
        halaman = page.page(h)
    except:
        h=1
        halaman = page.page(1)

    try:
        pengumuman = get_pengumuman_text()
    except:
        pengumuman = DEFAULT_PENGUMUMAN

    context = {
        'pengumuman':pengumuman,
        'blogs':blogs,
    }
    context.update(user_context)
    context.update(build_pagination_context(halaman, h))
    return render(request,'landing/all-blogs.html',context)

def detailBlog(request,id):
    try:
        blog = Blogs.objects.select_related('author').get(id=id)
    except Exception:
        messages.add_message(request,messages.SUCCESS,"Maaf, blogs yang kaka cari tidak ada...")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    user = get_authenticated_user(request)

    if request.method == "POST" and request.POST.get('comment_type') == "blog":
        comment_value = request.POST.get('comment', '').strip()
        if user is None:
            messages.add_message(request, messages.SUCCESS, "Silakan login terlebih dahulu untuk menambahkan komentar.")
        elif comment_value == "":
            messages.add_message(request, messages.SUCCESS, "Komentar tidak boleh kosong.")
        else:
            existing_comments = BlogComment.objects.filter(blog=blog, user=user).order_by('-updated_at')
            existing_comment = existing_comments.first()
            if existing_comment:
                existing_comment.comment = comment_value
                existing_comment.is_active = True
                existing_comment.is_publish = True
                existing_comment.save()
                existing_comments.exclude(id=existing_comment.id).delete()
                messages.add_message(request, messages.SUCCESS, "Komentar berhasil diperbarui.")
            else:
                BlogComment.objects.create(blog=blog, user=user, comment=comment_value)
                messages.add_message(request, messages.SUCCESS, "Komentar berhasil ditambahkan.")
        return HttpResponseRedirect(f"{reverse('detail_blog', args=[blog.id])}#blog-comments")
    
    user_context = build_user_view_context(
        user,
        include_cart=True,
        include_checked_cart=True,
        include_inbox=True,
    )
    
    try:
            pengumuman = get_pengumuman_text()
    except:
            pengumuman = DEFAULT_PENGUMUMAN

    prev = request.META.get('HTTP_REFERER')
    blog_comments = BlogComment.objects.filter(blog=blog, is_active=True, is_publish=True).select_related('user__userdetail').order_by('-created_at')
    blog_comments_page = get_comment_page(blog_comments, request.GET.get('comment_page', 1))

    context = {
            'pengumuman':pengumuman,
            'blog':blog,
            'prev':prev,
            'blog_comments_page': blog_comments_page,
        }
    context.update(user_context)
    return render(request,'landing/blog-detail.html',context)

def paymentProcess(request):
    if request.method == "POST":
        if request.user.is_authenticated:
            user = get_authenticated_user(request)
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
                mycart = MyCart.objects.filter(Q(user=user) & Q(is_checked=True)).select_related('book__onsalebook')
                for cart in mycart:
                    try:
                        book = cart.book
                        # pengecekan harga buku: apakah merupakan buku on sale?
                        try:
                            price = cart.book.onsalebook.nett_price
                        except OnSaleBook.DoesNotExist:
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
        user = get_authenticated_user(request)
        user_context = build_user_view_context(
            user,
            include_cart=True,
            include_checked_cart=True,
            include_inbox=True,
        )
        mycart = user_context['mycart']
        mycart_buy = mycart.filter(is_checked=True)
        jml_mcart_buy = mycart_buy.count()

        if(mycart_buy.count()==0) :
            return HttpResponseRedirect("/cart/")

        try:
            pengumuman = get_pengumuman_text()
        except:
            pengumuman = DEFAULT_PENGUMUMAN

        nomor_invoice = 'ltn'+str(datetime.datetime.now().year) + str(uuid.uuid4())

        total_bayar = 0

        for cart in mycart_buy:
            try:
                onsalebook = cart.book.onsalebook
                if onsalebook.is_active:
                    total_bayar += onsalebook.nett_price
                else:
                    total_bayar += cart.book.price
            except OnSaleBook.DoesNotExist:
                total_bayar += cart.book.price
        total_bayar = f"{int(total_bayar)}.00"
        context = {
                'pengumuman':pengumuman,
                'mycart_buy':mycart_buy,
                'nomor_invoice':nomor_invoice,
                'jml_mycart_buy':jml_mcart_buy,
                'total_bayar':total_bayar,
                'no_rekening':'01230254390',
                'nama_bank':'BCA',
                'nama_pemilik':'PT SULUH  CENDEKIA'
            }
        context.update(user_context)
        return render(request,'landing/payment.html',context)
    else:
        messages.add_message(request,messages.SUCCESS,'Ups.. sepertinya kaka login dari device lain? Silakan kaka login kembali di device ini untuk melanjutkan yah...')
        return HttpResponseRedirect('/cart/')
    
    
def bacaBukuKoleksi(request,id):
    try:
        if request.user.is_authenticated:
            user = get_authenticated_user(request)
            try:
                book = Books.objects.select_related('kategori').get(id=id)
            except:
                messages.add_message(request,messages.SUCCESS,'Buku yang kaka cari tidak ada...')
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))    
            
            try:
                userbook = UserBook.objects.get(Q(id_book=book) & Q(id_user=user))
            except:
                messages.add_message(request,messages.SUCCESS,'Karena ini buku berbayar, dan kaka belum memiliki di koleksi, kaka hanya bisa melihat preview sampul saja yah...')
                return HttpResponseRedirect(f'/book/?id={book.id}')

            if request.method == "POST" and request.POST.get('comment_type') == "book":
                comment_value = request.POST.get('comment', '').strip()
                if comment_value == "":
                    messages.add_message(request, messages.SUCCESS, "Komentar tidak boleh kosong.")
                else:
                    existing_comments = BookComment.objects.filter(book=book, user=user).order_by('-updated_at')
                    existing_comment = existing_comments.first()
                    if existing_comment:
                        existing_comment.comment = comment_value
                        existing_comment.is_active = True
                        existing_comment.is_publish = True
                        existing_comment.save()
                        existing_comments.exclude(id=existing_comment.id).delete()
                        messages.add_message(request, messages.SUCCESS, "Komentar berhasil diperbarui.")
                    else:
                        BookComment.objects.create(book=book, user=user, comment=comment_value)
                        messages.add_message(request, messages.SUCCESS, "Komentar berhasil ditambahkan.")
                p = request.GET.get('p', '1')
                return HttpResponseRedirect(f"{reverse('baca_buku_koleksi', args=[book.id])}?p={p}#book-comments")

            try:
                page = int(request.GET.get('p', userbook.last_page or 1))

                if page < 1:
                    page = 1
                if page>book.halaman:
                    page=book.halaman
                userbook.last_page=int(page)
                userbook.save()
            except:
                page=int(userbook.last_page)
                if page==0:
                    page=1
            
            user_context = build_user_view_context(user)

            max_page = book.halaman

            if page==1:
                prev=1
            else:
                prev=page-1
            
            next=page+1
            if(next>max_page):
                next=max_page

            try:
                pengumuman = get_pengumuman_text()
            except:
                pengumuman = DEFAULT_PENGUMUMAN

            context = {
                'pengumuman':pengumuman,
                'book':book,
                'next':next,
                'prev':prev,
                'page':page,
                'max_page':max_page,
                'current_page_image': f"/media/extract/pdf_full/{book.id}/{page}.jpg",
                'prev_page_image': f"/media/extract/pdf_full/{book.id}/{prev}.jpg" if page > 1 else None,
                'next_page_image': f"/media/extract/pdf_full/{book.id}/{next}.jpg" if page < max_page else None,
                'comments_page_obj': get_comment_page(
                    BookComment.objects.filter(book=book, is_active=True, is_publish=True).select_related('user__userdetail').order_by('-created_at'),
                    request.GET.get('comment_page', 1),
                ),
                'can_comment_book': True,
                'is_preview_reader': False,
                'book_reader_page_base': f"{reverse('baca_buku_koleksi', args=[book.id])}?p=",
            }
            context.update(user_context)

            if request.headers.get('HX-Request') == 'true':
                return render(request, 'landing/partials/baca-buku-panel.html', context)

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
        user_context = build_user_view_context(
            get_authenticated_user(request),
            include_koleksi=True,
        )
        koleksiku = user_context['koleksiku']

        page = Paginator(koleksiku,per_page=8)
        
        try:
            halaman = page.page(h)
        except:
            h=1
            halaman = page.page(1)

        try:
            pengumuman = get_pengumuman_text()
        except:
            pengumuman = DEFAULT_PENGUMUMAN

        context = {
            'pengumuman':pengumuman,
        }
        context.update(user_context)
        context.update(build_pagination_context(halaman, h))
        return render(request,'landing/all-koleksi.html',context)

    else:
        messages.add_message(request,messages.SUCCESS,'Untuk bisa melihat daftar koleksi, kaka harus login terlebih dahulu yah...')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def profileView(request):
    if request.user.is_authenticated:
        user_context = build_user_view_context(
            get_authenticated_user(request),
            include_koleksi=True,
        )
        try:
            pengumuman = get_pengumuman_text()
        except:
            pengumuman = DEFAULT_PENGUMUMAN

        context = {
            'pengumuman':pengumuman,
        }
        context.update(user_context)
        return render(request,'landing/profile.html',context)

    else:
        messages.add_message(request,messages.SUCCESS,'Untuk bisa melihat profile harus login terlebih dahulu kaka...')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def profileUpdate(request):
    if request.user.is_authenticated:
        user = get_authenticated_user(request)
        if request.method == "POST":
            formnya = FormUpdateProfile(data=request.POST,files=request.FILES)
            if formnya.is_valid():
                try:
                    # simpan file foto ke dalam uuid format
                    nama_file = str(uuid.uuid4())
                    #dapatkan extension file
                    extension = os.path.splitext(request.FILES['photo'].name)[1].lstrip('.')

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

        user_context = build_user_view_context(
            user,
            include_koleksi=True,
        )
        userdetail = UserDetail.objects.get(user=user)
        updateprofile = FormUpdateProfile(instance=userdetail)
        try:
            pengumuman = get_pengumuman_text()
        except:
            pengumuman = DEFAULT_PENGUMUMAN

        context = {
            'pengumuman':pengumuman,
            'updateprofile':updateprofile
        }
        context.update(user_context)
        return render(request,'landing/profile_edit.html',context)

    else:
        messages.add_message(request,messages.SUCCESS,'Untuk bisa melihat profile harus login terlebih dahulu kaka...')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def listPayment(request):
    if request.user.is_authenticated:
        user = get_authenticated_user(request)
        user_context = build_user_view_context(
            user,
            include_cart=True,
            include_checked_cart=True,
            include_inbox=True,
        )
        mypayment = MyPayment.objects.filter(user=user).prefetch_related(
            Prefetch(
                'mypaymentdetail_set',
                queryset=MyPaymentDetail.objects.select_related('book').order_by('id'),
                to_attr='detail_items',
            )
        ).order_by('-created_at')
        jml_mypayment = mypayment.count()

        try:
            pengumuman = get_pengumuman_text()
        except:
            pengumuman = DEFAULT_PENGUMUMAN
        
        context = {
            'pengumuman':pengumuman,
            'mypayment':mypayment,
            'jml_mypayment':jml_mypayment,
        }
        context.update(user_context)
        return render(request,'landing/detail-payment.html',context)
    else:
        messages.add_message(request,messages.SUCCESS,'Ups.. sepertinya kaka login dari device lain? Silakan kaka login kembali di device ini untuk melanjutkan yah...')
        return HttpResponseRedirect('/')

def gantiPasswordPage(request):
    if request.user.is_authenticated:
        user = get_authenticated_user(request)

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

        user_context = build_user_view_context(
            user,
            include_koleksi=True,
        )
        try:
            pengumuman = get_pengumuman_text()
        except:
            pengumuman = DEFAULT_PENGUMUMAN

        context = {
            'pengumuman':pengumuman,
        }
        context.update(user_context)
        return render(request,'landing/change_password.html',context)

    else:
        messages.add_message(request,messages.SUCCESS,'Untuk bisa mengganti password harus login terlebih dahulu kaka...')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def pencarianInfo(request):
    try:
        if request.method=="POST":
            keyword = request.POST['s']

            blog = Blogs.objects.filter(
                Q(header__icontains=keyword) | Q(body__icontains=keyword)
            ).select_related('author')
            book = Books.objects.filter(
                Q(judul__icontains=keyword) | Q(deskripsi__icontains=keyword) | Q(sinopsis__icontains=keyword) | Q(pengarang__icontains=keyword)
            ).select_related('kategori', 'onsalebook')

            jumlah_blog = blog.count()
            jumlah_book = book.count()
        else:
            return HttpResponseRedirect('/')
    except:
        return HttpResponseRedirect('/')
    
    try:
            pengumuman = get_pengumuman_text()
    except:
            pengumuman = DEFAULT_PENGUMUMAN

    user_context = build_user_view_context(
        get_authenticated_user(request),
        include_userbook_preview=True,
    )
    
    context = {
        'keyword':keyword,
        'book':book,
        'blog':blog,
        'jumlah_blog':jumlah_blog,
        'jumlah_book':jumlah_book,
        'pengumuman':pengumuman
    }
    context.update(user_context)
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
            pengumuman = get_pengumuman_text()
    except:
            pengumuman = DEFAULT_PENGUMUMAN

    user_context = build_user_view_context(
        get_authenticated_user(request),
        include_userbook_preview=True,
    )
    
    context = {
        'bulan_now':bulan_now,
        'total_now':total_now,
        'pengumuman':pengumuman
    }
    context.update(user_context)
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
            pengumuman = get_pengumuman_text()
    except:
            pengumuman = DEFAULT_PENGUMUMAN

    # jjka data donasi sudah ada maka dijumlah
    if len(data_donasi_now)>0:
        total_donasi_now = MyDonation.objects.all().filter(Q(updated_at__month=bulan_donasi_now) & Q(updated_at__year=tahun_donasi_now) & Q(is_verified=True)).aggregate(jumlah=Sum('nilai'))
        total_now = total_donasi_now['jumlah']
    else:
        # kalau belum ada data donasi di nolkan
        total_now=0
    bulan_now = bulanTeks(bulan_donasi_now) + f" {str(tahun_donasi_now)}"

    formmydonation = FormMyDonation()

    user_context = build_user_view_context(
        get_authenticated_user(request),
        include_userbook_preview=True,
    )
    
    context = {
        'bulan_now':bulan_now,
        'total_now':total_now,
        'no_rekening':'01230254390',
        'nama_bank':'BCA',
        'nama_pemilik':'PT SULUH  CENDEKIA',
        'form':formmydonation,
        'donatur':data_donasi_now,
        'pengumuman':pengumuman
    }
    context.update(user_context)
    return render(request,'landing/form-donasi.html',context)
