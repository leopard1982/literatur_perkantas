from django.db import models
from django.contrib.auth.models import  User
from django.db.models import Sum,Count,F
import uuid
import hashlib
from pdf2image import convert_from_bytes
from django.conf import settings
import os
import datetime
from django.contrib import messages

colornya = [
	('pink','pink'),
	('blue','blue'),
	('red','red'),
	('yellow','yellow'),
	('green','green'),
	('chocolate','chocolate'),
	('cyan','cyan'),
	('magenta','magenta'),
	('purple','purple'),
	('violet','violet'),
	('grey','grey')
]

payment = [
	('BCA','BCA'),
	('Mandiri','Mandiri')
]

leveling = [
	('silver','silver'),
	('gold','gold'),
	('platinum','platinum')
]

tipe = [
	('free','free'),
	('subscribe','subscribe'),
	('buy','buy')
]

#buku a b c --> silver --> 20rb --> semi google point ditandai
#tanda 1 buku dibaca --> totalan 10.000.000 --> buku sering dibaca --> % keuntungan 
#buku d e f --> gold --> 50rb 
#buku g h i --> platinum --> 100rb
##counting klik buku reset setiap awal bulan
#preview...
#buku lifetime --> buku i

class Category(models.Model):
	nama = models.CharField(max_length=30,default="")
	keterangan = models.CharField(max_length=100,default="")
	gambar = models.ImageField(upload_to='gambar_category',blank=True,null=True)

	def __str__(self):
		return f"{self.nama}"

class UserDetail(models.Model):
	user= models.OneToOneField(User,on_delete=models.DO_NOTHING)
	id_customer = models.UUIDField(auto_created=True,editable=False,default=uuid.uuid4)
	id_perkantas = models.CharField(max_length=100,null=True,blank=True,verbose_name="ID Data Perkantas")
	alias = models.CharField(max_length=256,null=True,blank=True,verbose_name="Nama Panggilan")
	nama_lengkap = models.CharField(max_length=200,null=True,blank=True)
	birthday = models.DateField(auto_now_add=False,blank=True,null=True)
	photo = models.ImageField(upload_to='profile',null=True,blank=True)
	total_poin = models.PositiveSmallIntegerField(default=0)
	total_book = models.PositiveSmallIntegerField(default=0)
	updated_at = models.DateTimeField(auto_now=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.nama_lengkap}"

class Books(models.Model):
	id = models.UUIDField(primary_key=True,editable=False,auto_created=True,default=uuid.uuid4,db_index=True)
	judul = models.CharField(max_length=100,default="",verbose_name="Nama Buku")
	pengarang = models.CharField(max_length=100,default="",verbose_name="Pengarang Buku")
	price = models.PositiveIntegerField(default=0,verbose_name="Harga Buku")
	isbn = models.CharField(max_length=50,default="",verbose_name="Kode ISBN")
	halaman= models.PositiveIntegerField(default=0,verbose_name="Jumlah Halaman")
	deskripsi = models.TextField(default="",verbose_name="Deskripsi Singkat")
	point = models.PositiveIntegerField(default=0,verbose_name="Point")
	pdf_full = models.FileField(upload_to="pdf_full",verbose_name="File PDF Full",blank=True,null=True)
	kategori = models.ForeignKey(Category,on_delete=models.DO_NOTHING)
	view = models.PositiveBigIntegerField(default=0)
	is_update_pdf = models.BooleanField(default=False,verbose_name='IS UPDATE ALL DATA?')
	is_update_info = models.BooleanField(default=False,verbose_name="IS UPDATE INFO ONLY")
	is_best_seller = models.BooleanField(default=True)
	updated_at = models.DateTimeField(auto_now=True)
	created_at = models.DateTimeField(auto_now_add=True)
	sinopsis = models.TextField(blank=True,null=True)

	def save(self,*args,**kwargs):
		if self.is_update_pdf and self.pdf_full!=None:
			try:
				OnSaleBook.objects.all().filter(book=Books.objects.get(id=self.id)).delete()
			except:
				pass
			self.is_update_pdf=False
			super(Books,self).save(*args,**kwargs)
			
			#road to path
			#lokasi file pdf
			lokasi_pdf = os.path.join(settings.BASE_DIR,"media",self.pdf_full.name)
			#lokasi path extract image
			lokasi_images = os.path.join(settings.BASE_DIR,"media","extract","pdf_full",str(self.id))
			

			#create direktori baru untuk simpan file extract jpg
			print(f"create direktori start: {datetime.datetime.now()}")
			try:
				os.makedirs(lokasi_images)
			except:
				#hapus list file yang lama
				for f in os.listdir(lokasi_images):
					os.remove(os.path.join(lokasi_images,f))
			
			#createppm baru			
			print(f"create ppm baru start: {datetime.datetime.now()}")
			images = convert_from_bytes(open(lokasi_pdf,'rb').read(),output_folder=lokasi_images)
			
			#simpan setiap file ppm jadi jpg
			print(f"create jpg baru start: {datetime.datetime.now()}")
			for nomor,image in enumerate(images):
				#save as jpeg
				image.save(os.path.join(lokasi_images,str(nomor+1)+".jpg"),"JPEG")
			
			#hapus file ppm
			print(f"hapus ppm lama start: {datetime.datetime.now()}")
			for f in os.listdir(lokasi_images):
				# print(f)
				if(f.split('.')[1]=="ppm"):
					os.remove(os.path.join(lokasi_images,f))
			print(f"selesai proses: {datetime.datetime.now()}")

			#hapus file pdfnya
			os.remove(lokasi_pdf)
		elif self.is_update_info:
			OnSaleBook.objects.all().filter(book=Books.objects.get(id=self.id)).delete()
			super(Books,self).save(*args,**kwargs)

	def __str__(self):
		return f"{self.judul}"
	
class MyWishlist(models.Model):
	user = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
	book = models.ForeignKey(Books,on_delete=models.SET_NULL,null=True)

	class Meta:
		unique_together = ['user','book']
	
	def __str__(self):
		return f"{self.book.judul} - {self.book.pengarang}"
	
class MyCart(models.Model):
	user = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
	book = models.ForeignKey(Books,on_delete=models.SET_NULL,null=True)
	is_checked = models.BooleanField(default=True)

	class Meta:
		unique_together = ['user','book']
	
	def __str__(self):
		return f"{self.book.judul} - {self.book.pengarang}"

class MyPayment(models.Model):
	payment = models.CharField(max_length=300,default="",primary_key=True,db_index=True)
	user = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
	total = models.DecimalField(decimal_places=2,max_digits=30,default=0)
	bukti = models.CharField(max_length=300,default="",null=True,blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	jumlah_buku = models.IntegerField(default=0)
	jumlah_point = models.IntegerField(default=0)
	is_verified = models.BooleanField(default=False)
	is_canceled = models.BooleanField(default=False)
	pemroses = models.CharField(max_length=100,null=True,blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.payment} - {self.user.username} - {self.total}"	
	
	def save(self,*args,**kwargs):
		super(MyPayment,self).save(*args,**kwargs)
		#jika verified
		if self.is_verified and not self.is_canceled:
			#update status buku detail jadi aktif
			mypaymentdetail=MyPaymentDetail.objects.all().filter(payment=self.payment)
			mypaymentdetail.update(is_active=True)
			
			mypayment = MyPayment.objects.get(payment=self.payment)
			#tambahkan buku ke UserBook
			
			for detail in mypaymentdetail:
				try:
					userbook = UserBook()
					userbook.id_book = detail.book
					userbook.id_user=self.user
					userbook.payment= mypayment
					userbook.save()
				except Exception as ex:
					print(ex)

			# buat pesan inbox
			inboxmessage = inboxMessage()
			inboxmessage.user=self.user
			inboxmessage.header="Pembayaran Selesai Dikonfirmasi"
			inboxmessage.body=f"Selamat kaka, untuk pembayaran sebesar {self.total} untuk nomor invoice {self.payment} sudah selesai dikonfirmasi, dan buku sudah bisa kaka baca. Terima kasih, Tuhan memberkati!"
			inboxmessage.save()

			#simpan pemroses
			self.pemroses=self.user.username
			super(MyPayment,self).save(*args,**kwargs)
		
		# jika tidak verified
		if not self.is_verified and self.is_canceled:
			#update status buku detail jadi aktif
			mypaymentdetail=MyPaymentDetail.objects.all().filter(payment=self.payment)
			mypaymentdetail.update(is_active=False)
			
			#hapus  UserBook
			UserBook.objects.all().filter(payment=MyPayment.objects.get(payment=self.payment)).delete()

			# buat pesan inbox
			inboxmessage = inboxMessage()
			inboxmessage.user=self.user
			inboxmessage.header="Pembayaran Gagal Dikonfirmasi"
			inboxmessage.body=f"Maaf kaka, untuk pembayaran sebesar {self.total} dengan nomor invoice {self.payment} tidak berhasil diverifikasi, karena bukti transfer tidak sesuai. Boleh kaka kembali kirimkan foto yang sesuai ke nomor whatsapp admin Litanas di nomor: +6281291508616. Terima kasih, Tuhan memberkati!"
			inboxmessage.save()

			#simpan pemroses
			self.pemroses=self.user.username
			super(MyPayment,self).save(*args,**kwargs)


class MyPaymentDetail(models.Model):
	payment = models.ForeignKey(MyPayment,on_delete=models.CASCADE)
	book = models.ForeignKey(Books,on_delete=models.SET_NULL,null=True)
	is_active = models.BooleanField(default=False)

	def __str__(self):
		return f"{self.payment.payment} - {self.book.judul}"


class FeaturedBook(models.Model):
	book = models.OneToOneField(Books,on_delete=models.CASCADE)
	start_date = models.DateField(auto_now_add=False, verbose_name="Tanggal Mulai")
	end_date = models.DateField(auto_now_add=False,verbose_name="Tanggal Selesai")
	is_active = models.BooleanField(default=True, verbose_name="IS ACTIVE?")
	header = models.CharField(default="",blank=False,null=False,max_length=50)
	body = models.CharField(default="",null=False,blank=False,max_length=100)
	updated_at = models.DateTimeField(auto_now=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.book.judul} - {self.header} - {self.body}"

class OnSaleBook(models.Model):
	book = models.OneToOneField(Books,on_delete=models.CASCADE)
	start_date = models.DateField(auto_now_add=False, verbose_name="Tanggal Mulai")
	end_date = models.DateField(auto_now_add=False,verbose_name="Tanggal Selesai")
	is_active = models.BooleanField(default=True, verbose_name="IS ACTIVE?")
	discount = models.DecimalField(decimal_places=2,max_digits=4)
	header = models.CharField(default="",blank=False,null=False,max_length=50)
	body = models.CharField(default="",null=False,blank=False,max_length=100)
	nett_price = models.DecimalField(max_digits=15,decimal_places=2,default=0)
	updated_at = models.DateTimeField(auto_now=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def save(self,*args,**kwargs):
		self.nett_price=self.book.price-self.discount*self.book.price/100
		super(OnSaleBook,self).save(*args,**kwargs)


class BooksPrevJPG(models.Model):
	id_books = models.ForeignKey(Books,on_delete=models.CASCADE)
	halaman = models.PositiveSmallIntegerField(default=0)
	image = models.ImageField(upload_to=id_books)

class BooksFullJPG(models.Model):
	id_books = models.ForeignKey(Books,on_delete=models.CASCADE)
	halaman = models.PositiveSmallIntegerField(default=0)
	image = models.ImageField(upload_to=id_books)

class BookReview(models.Model):
	id = models.UUIDField(primary_key=True,auto_created=True,editable=False)
	id_buku = models.ForeignKey(Books,on_delete=models.RESTRICT,related_name="id_buku")
	id_customer = models.ForeignKey(UserDetail,on_delete=models.RESTRICT)
	review = models.TextField(max_length=200)
	updated_review = models.DateField(auto_now_add=True)
	is_published = models.BooleanField(default=False)


	def __str__(self):
		return f"{self.id_customer.nama_lengkap}"

	class Meta:
		unique_together = ['id_buku','id_customer']

		

class UserBook(models.Model):
	id_book = models.ForeignKey(Books,on_delete=models.RESTRICT)
	id_user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="id_user",null=True,blank=True)
	last_page = models.PositiveSmallIntegerField(default=0)
	payment = models.ForeignKey(MyPayment,on_delete=models.RESTRICT,related_name="payment_book")

	def __str__(self):
		return f"{self.id_book}"
	
	class Meta:
		unique_together = ['id_book','id_user']

class customerBookmark(models.Model):
	id_bookmark = models.UUIDField(primary_key=True,auto_created=True,editable=False)
	id_userbook = models.ForeignKey(UserBook,on_delete=models.RESTRICT)
	page = models.PositiveSmallIntegerField(default=1)
	color = models.CharField(max_length=20,choices=colornya)
	note = models.TextField(max_length=2000,null=True,blank=True)
	is_penting = models.BooleanField(default=False)

	def __str__(self):
		return f"{self.note}"
	
	class Meta:
		unique_together = ['page','id_userbook']

class PageReview(models.Model):
	id = models.UUIDField(auto_created=True,primary_key=True,editable=False,default=uuid.uuid4)
	user = models.OneToOneField(User,on_delete=models.DO_NOTHING)
	review = models.CharField(max_length=400,null=True,blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	is_active = models.BooleanField(default=True)

	def __str__(self):
		return f"{self.user.userdetail.nama_lengkap} - {self.review}"

class Pengumuman(models.Model):
	pengumuman = models.CharField(max_length=255,default="",blank=False,null=False)

	def save(self,*args,**kwargs):
		self.pengumuman = self.pengumuman.upper()
		super(Pengumuman,self).save(*args,**kwargs)


class Instagram(models.Model):
	gambar = models.ImageField(upload_to="gambar_instagram",blank=False,null=False)
	link = models.CharField(max_length=200,default="")


class LupaPassword(models.Model):
	id = models.UUIDField(editable=False,auto_created=True,default=uuid.uuid4,primary_key=True)
	email = models.CharField(max_length=200,default="")
	is_used = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	expired = models.DateTimeField(auto_now_add=False)

	def save(self,*args,**kwargs):
		self.expired=datetime.datetime.now() + datetime.timedelta(minutes=settings.EXPIRED_MINUTES)
		super(LupaPassword,self).save(*args,**kwargs)

	def __str__(self):
		return f"{self.email} - {self.is_used} - {self.expired}"

class BannerIklan(models.Model):
	id =models.UUIDField(primary_key=True,editable=False,auto_created=True,default=uuid.uuid4)
	gambar = models.ImageField(upload_to="iklan_pc",null=True,blank=True)
	start_live = models.DateTimeField(auto_now_add=False,blank=True,null=True)
	end_live = models.DateTimeField(auto_now_add=False,blank=True,null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	link = models.CharField(max_length=200,default="https://")
	header = models.CharField(max_length=200,default="")
	body = models.CharField(max_length=200,default="")

	def __str__(self):
		return f"{self.header} - {self.link} - {self.start_live} - {self.end_live}"

class inboxMessage(models.Model):
	user = models.ForeignKey(User,on_delete=models.RESTRICT)
	header = models.CharField(max_length=50,default="")
	body = models.CharField(max_length=200,default="")
	created_at = models.DateTimeField(auto_now_add=True)
	expired_at = models.DateTimeField(auto_now_add=True)

	def save(self,*args,**kwargs):
		super(inboxMessage,self).save(*args,**kwargs)
		self.expired_at = self.created_at + datetime.timedelta(weeks=52)
		super(inboxMessage,self).save(*args,**kwargs)

	def __str__(self):
		return f"{self.user} - {self.header} - {self.body} "


TIPE_BLOGS = [
	('Renungan','Renungan'),
	('Kisah Buku','Kisah Buku')
]

class Blogs(models.Model):
	id = models.UUIDField(auto_created=True,primary_key=True,editable=False,default=uuid.uuid4)
	tipe = models.CharField(max_length=20,choices=TIPE_BLOGS,default="Renungan")
	author = models.ForeignKey(User,on_delete=models.RESTRICT,verbose_name="Pengarang")
	image = models.ImageField(upload_to='blogs',null=True,blank=True,verbose_name="Gambar Tema Blog")
	header = models.CharField(max_length=50,verbose_name="Judul Blog")
	body = models.TextField(verbose_name="Isi Blog")
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.author} - {self.header}"

class DaftarPayment(models.Model):
	user = models.ForeignKey(User,on_delete=models.RESTRICT)
	payment = models.ForeignKey(MyPayment,on_delete=models.RESTRICT,related_name="Pembayaran")
	sisa = models.IntegerField(default=0)
	tgl_trf_sisa = models.DateTimeField(auto_now_add=False,null=True,blank=True)
	pemroses = models.CharField(max_length=100,null=True,blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)