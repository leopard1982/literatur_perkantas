from django import forms
from django.contrib.auth.models import User
from django.db.models import Q

from literatur.models import BlogPost, Blogs, Books, Category, Instagram, MobileBroadcast, OnSaleBook, Pengumuman

from .roles import CMS_ROLE_CHOICES

TEXT_ATTRS = {'class': 'form-control'}
SELECT_ATTRS = {'class': 'form-select'}


class BookForm(forms.ModelForm):
    class Meta:
        model = Books
        fields = [
            'judul', 'pengarang', 'isbn', 'kategori', 'price',
            'halaman', 'point', 'persen_penulis', 'persen_litanas', 'deskripsi', 'sinopsis', 'pdf_full',
        ]
        widgets = {
            'judul': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Judul buku', 'required': 'required'}),
            'pengarang': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Nama pengarang', 'required': 'required'}),
            'isbn': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Kode ISBN'}),
            'kategori': forms.Select(attrs=SELECT_ATTRS),
            'price': forms.NumberInput(attrs={**TEXT_ATTRS, 'min': 0, 'required': 'required'}),
            'halaman': forms.NumberInput(attrs={**TEXT_ATTRS, 'min': 0}),
            'point': forms.NumberInput(attrs={**TEXT_ATTRS, 'min': 0}),
            'persen_penulis': forms.NumberInput(attrs={**TEXT_ATTRS, 'min': 0, 'max': 100, 'step': '0.01', 'required': 'required'}),
            'persen_litanas': forms.NumberInput(attrs={**TEXT_ATTRS, 'min': 0, 'max': 100, 'step': '0.01', 'required': 'required'}),
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
            'persen_penulis': 'Bagi Hasil Penulis (%)',
            'persen_litanas': 'Bagi Hasil Litanas (%)',
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


class MobileBroadcastForm(forms.ModelForm):
    class Meta:
        model = MobileBroadcast
        fields = ['jenis', 'header', 'body']
        widgets = {
            'jenis': forms.Select(attrs={'class': 'form-select'}),
            'header': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Judul notifikasi', 'required': 'required', 'maxlength': 50}),
            'body': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Isi notifikasi', 'required': 'required', 'maxlength': 200}),
        }
        labels = {'jenis': 'Jenis', 'header': 'Judul', 'body': 'Isi'}


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


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['judul', 'pengarang', 'isi', 'is_archived']
        widgets = {
            'judul': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Judul blog', 'required': 'required', 'maxlength': 150}),
            'pengarang': forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Nama pengarang', 'required': 'required', 'maxlength': 100}),
            'isi': forms.Textarea(attrs={**TEXT_ATTRS, 'rows': 12, 'placeholder': 'Tulis isi blog di sini...'}),
            'is_archived': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'judul': 'Judul',
            'pengarang': 'Pengarang',
            'isi': 'Isi Blog',
            'is_archived': 'Arsipkan (tidak tampil di halaman utama)',
        }


class QrisUploadForm(forms.Form):
    """Unggah QRIS baru. Isi file diperiksa dengan Pillow (bukan hanya ekstensi / content-type)."""
    MAX_BYTES = 3 * 1024 * 1024
    FORMATS = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}

    tujuan = forms.ChoiceField(choices=[('pembelian', 'Pembelian Buku'), ('donasi', 'Donasi')], widget=forms.HiddenInput)
    gambar = forms.FileField(label='Gambar QRIS', widget=forms.FileInput(attrs={**TEXT_ATTRS, 'accept': 'image/jpeg,image/png,image/webp', 'required': 'required'}))
    keterangan = forms.CharField(label='Keterangan (opsional)', required=False, max_length=200,
                                 widget=forms.TextInput(attrs={**TEXT_ATTRS, 'placeholder': 'Contoh: QRIS BCA a.n. PT Suluh Cendekia', 'maxlength': 200}))

    def clean_gambar(self):
        from PIL import Image, UnidentifiedImageError
        f = self.cleaned_data['gambar']
        if f.size > self.MAX_BYTES:
            raise forms.ValidationError('Ukuran gambar maksimal 3 MB.')
        try:
            with Image.open(f) as im:
                im.verify()
            f.seek(0)
            with Image.open(f) as im:
                fmt, (w, h) = im.format, im.size
        except (UnidentifiedImageError, OSError, SyntaxError):
            raise forms.ValidationError('File bukan gambar yang valid.')
        f.seek(0)
        if fmt not in self.FORMATS:
            raise forms.ValidationError('Gunakan gambar JPG, PNG, atau WEBP.')
        if min(w, h) < 200 or max(w, h) > 6000:
            raise forms.ValidationError('Ukuran gambar harus antara 200 dan 6000 piksel.')
        f.ext = self.FORMATS[fmt]
        return f
