from django.db import models
from django.contrib.auth.models import  User
from django.db.models import Sum,Count,F
import uuid
import hashlib
from pdf2image import convert_from_bytes
from django.conf import settings
import os
import datetime

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

kategori = [
	('PA','PA'),
	('Pemuridan','Pemuridan')
]


#buku a b c --> silver --> 20rb --> semi google point ditandai
#tanda 1 buku dibaca --> totalan 10.000.000 --> buku sering dibaca --> % keuntungan 
#buku d e f --> gold --> 50rb 
#buku g h i --> platinum --> 100rb
##counting klik buku reset setiap awal bulan
#preview...
#buku lifetime --> buku i

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

	def __str__(self):
		return f"{self.nama_lengkap}"

class Books(models.Model):
	id = models.UUIDField(primary_key=True,editable=False,auto_created=True)
	judul = models.CharField(max_length=100,default="",verbose_name="Nama Buku")
	pengarang = models.CharField(max_length=100,default="",verbose_name="Pengarang Buku")
	price = models.PositiveIntegerField(default=0,verbose_name="Harga Buku")
	isbn = models.CharField(max_length=50,default="",verbose_name="Kode ISBN")
	halaman= models.PositiveIntegerField(default=0,verbose_name="Jumlah Halaman")
	deskripsi = models.TextField(default="",verbose_name="Deskripsi Singkat")
	point = models.PositiveIntegerField(default=0,verbose_name="Point")
	tipe = models.CharField(max_length=20,default="",choices=tipe)
	pdf_full = models.FileField(upload_to="pdf_full",verbose_name="File PDF Full")
	pdf_prev = models.FileField(upload_to="pdf_prev",verbose_name="File PDF Preview")
	kategori = models.CharField(max_length=20,choices=kategori)
	view = models.PositiveBigIntegerField(default=0)
	is_update_prev = models.BooleanField(default=False,blank=True,verbose_name='IS UPDATE PDF PREVIEW?')
	is_update_full = models.BooleanField(default=False,blank=True,verbose_name='IS UPDATE PDF FULL?')
	is_new = models.BooleanField(default=False,blank=True,verbose_name='IS CREATE NEW?')
	is_bestseller = models.BooleanField(default=False)
	is_discount = models.BooleanField(default=False)
	discount = models.DecimalField(decimal_places=2,max_digits=5,default=0)
	is_featured = models.BooleanField(default=False)
	

	def save(self,*args,**kwargs):
		if self.is_update_full:
			self.is_update_full=False
			super(Books,self).save(*args,**kwargs)
			
			#road to path
			#lokasi file pdf
			lokasi_pdf = os.path.join(settings.BASE_DIR,"media",self.pdf_full.name)
			#lokasi path extract image
			lokasi_images = os.path.join(settings.BASE_DIR,"media","extract","pdf_full",self.id)
			

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

		if self.is_update_prev:
			self.is_update_prev=True
			super(Books,self).save(*args,**kwargs)

	def __str__(self):
		return f"{self.judul}"
	
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


# Create your models here.

		

class UserBook(models.Model):
	id_book = models.ForeignKey(Books,on_delete=models.RESTRICT)
	id_user = models.ForeignKey(UserDetail,on_delete=models.CASCADE)
	last_page = models.PositiveSmallIntegerField(default=0)
	booked_date = models.DateField(auto_now_add=False,blank=True,null=True)
	payment = models.CharField(max_length=20,choices=payment)
	payment_code = models.CharField(max_length=100,null=True,blank=True)
	point = models.PositiveSmallIntegerField(default=0)

	def save(self,*args,**kwargs):
		self.point = self.id_book.point
		super(UserBook,self).save(*args,**kwargs)
		total_point = UserBook.objects.all().filter(id_user=self.id_user).aggregate(jumlah=Sum('point'))
		print(self.id_user)
		print(total_point['jumlah'])
		total_book = UserBook.objects.all().filter(id_user=self.id_user).aggregate(jumlah=Count('point'))
		print(total_book['jumlah'])
		UserDetail.objects.all().filter(username=self.id_user.username).update(total_poin=total_point['jumlah'],total_book=total_book['jumlah'])
		

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
	