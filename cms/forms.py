from django import forms
from django.contrib.auth.models import User
from django.db.models import Q

from literatur.models import Blogs, Books, Category, Instagram, OnSaleBook, Pengumuman

from .roles import CMS_ROLE_CHOICES

TEXT_ATTRS = {'class': 'form-control'}
SELECT_ATTRS = {'class': 'form-select'}


class BookForm(forms.ModelForm):
    class Meta:
        model = Books
        fields = [
            'judul', 'pengarang', 'isbn', 'kategori', 'price',
            'halaman', 'point', 'deskripsi', 'sinopsis', 'pdf_full',
        ]
        widgets = {
            'judul': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Judul buku', 'required': 'required'}),
            'pengarang': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Nama pengarang', 'required': 'required'}),
            'isbn': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Kode ISBN'}),
            'kategori': forms.Select(attrs=SELECT_ATTRS),
            'price': forms.NumberInput(attrs={**TEXT_ATTRS, 'min': 0, 'required': 'required'}),
            'halaman': forms.NumberInput(attrs={**TEXT_ATTRS, 'min': 0}),
            'point': forms.NumberInput(attrs={**TEXT_ATTRS, 'min': 0}),
            'deskripsi': forms.Textarea(attrs={**TEXT_ATTRS, 'rows': 3, 'placeholder': 'Deskripsi singkat buku'}),
            'sinopsis': forms.Textarea(attrs={**TEXT_ATTRS, 'rows': 5, 'placeholder': 'Sinopsis lengkap buku'}),
            'pdf_full': forms.FileInput(attrs={**TEXT_ATTRS, 'accept': 'application/pdf'}),
        }
        labels = {
            'judul': 'Judul Buku',
            'pengarang': 'Pengarang',
            'isbn': 'Kode ISBN',
            'kategori': 'Kategori',
            'price': 'Harga (Rp)',
            'halaman': 'Jumlah Halaman',
            'point': 'Point',
            'deskripsi': 'Deskripsi Singkat',
            'sinopsis': 'Sinopsis',
            'pdf_full': 'File PDF Full (unggah ulang jika ingin memperbarui isi buku)',
        }


class CategoryQuickForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['nama', 'keterangan', 'gambar']
        widgets = {
            'nama': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Nama kategori', 'required': 'required'}),
            'keterangan': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Keterangan singkat'}),
            'gambar': forms.FileInput(attrs={**TEXT_ATTRS, 'accept': 'image/*'}),
        }


class OnSaleForm(forms.ModelForm):
    class Meta:
        model = OnSaleBook
        fields = ['book', 'discount', 'start_date', 'end_date', 'header', 'body', 'is_active']
        widgets = {
            'book': forms.Select(attrs=SELECT_ATTRS),
            'discount': forms.NumberInput(attrs={**TEXT_ATTRS, 'min': 0, 'max': 99, 'step': '0.01', 'required': 'required'}),
            'start_date': forms.DateInput(attrs={**TEXT_ATTRS, 'type': 'date', 'required': 'required'}),
            'end_date': forms.DateInput(attrs={**TEXT_ATTRS, 'type': 'date', 'required': 'required'}),
            'header': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Judul promo', 'required': 'required'}),
            'body': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Deskripsi singkat promo', 'required': 'required'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'book': 'Buku',
            'discount': 'Diskon (%)',
            'start_date': 'Tanggal Mulai',
            'end_date': 'Tanggal Selesai',
            'header': 'Judul Promo',
            'body': 'Deskripsi Promo',
            'is_active': 'Aktifkan Promo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Books.objects.all().order_by('judul')
        if self.instance and self.instance.pk:
            queryset = queryset.filter(Q(onsalebook__isnull=True) | Q(pk=self.instance.book_id))
        else:
            queryset = queryset.filter(onsalebook__isnull=True)
        self.fields['book'].queryset = queryset


class InstagramForm(forms.ModelForm):
    class Meta:
        model = Instagram
        fields = ['gambar', 'link', 'is_active']
        widgets = {
            'gambar': forms.FileInput(attrs={**TEXT_ATTRS, 'accept': 'image/*'}),
            'link': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'https://www.instagram.com/p/...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'gambar': 'Foto Instagram',
            'link': 'Link Postingan Instagram',
            'is_active': 'Aktif (tampilkan di halaman utama)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.gambar:
            self.fields['gambar'].required = False


class PengumumanForm(forms.ModelForm):
    class Meta:
        model = Pengumuman
        fields = ['pengumuman']
        widgets = {
            'pengumuman': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Teks pengumuman berjalan', 'required': 'required', 'maxlength': 255}),
        }
        labels = {
            'pengumuman': 'Teks Pengumuman',
        }


class CmsUserCreateForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Username login CMS', 'required': 'required'}),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={**TEXT_ATTRS, 'placeholder': 'Email (opsional)'}),
    )
    nama_lengkap = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Nama lengkap (opsional)'}),
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={**TEXT_ATTRS, 'placeholder': 'Minimal 8 karakter', 'required': 'required'}),
    )
    role = forms.ChoiceField(
        choices=CMS_ROLE_CHOICES,
        widget=forms.Select(attrs=SELECT_ATTRS),
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Username ini sudah digunakan, silakan pilih username lain.')
        return username


class CoretanPenaForm(forms.ModelForm):
    class Meta:
        model = Blogs
        fields = ['header', 'image', 'body']
        widgets = {
            'header': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Judul coretan pena', 'required': 'required'}),
            'image': forms.FileInput(attrs={**TEXT_ATTRS, 'accept': 'image/*'}),
            'body': forms.Textarea(attrs={**TEXT_ATTRS, 'rows': 10, 'placeholder': 'Tulis coretan pena kaka di sini...', 'required': 'required'}),
        }
        labels = {
            'header': 'Judul',
            'image': 'Gambar Tema (opsional)',
            'body': 'Isi Tulisan',
        }
