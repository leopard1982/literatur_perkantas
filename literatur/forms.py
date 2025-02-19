from django import forms
from .models import UserDetail, MyDonation

class FormUpdateProfile(forms.ModelForm):
    class Meta:
        model = UserDetail
        fields = ['nama_lengkap','birthday','photo','no_whatsapp','pekerjaan','alamat']

        widgets = {
            'nama_lengkap':forms.TextInput(attrs={
                'class':'form-control fs-6 fw-bold',
                'placeholder':'Masukkan Nama Lengkap',
                'minlength':5,
                'required':'required'
            }),
            'birthday':forms.DateInput(
                attrs={
                    'type':'date',
                    'class':'form-control fs-6 fw-bold'
                }
            ),
            'photo':forms.FileInput(
                attrs={
                    'class':'form-control fs-6 fw-bold',
                    'accept':'image/*'
                }
            ),
            'no_whatsapp': forms.TextInput(
                attrs={
                    'type':'number',
                    'class':'form-control fs-6 fw-bold',
                    'placeholder':'Masukkan nomor whatsapp',
                    'required':'required'
                }
            ),
            'pekerjaan': forms.TextInput(
                attrs={
                    'class':'form-control fs-6 fw-bold',
                    'placeholder':'masukkan pekerjaan',
                    'required':'required'
                }
            ),
            'alamat': forms.TextInput(
                attrs={
                    'class':'form-control fs-6 fw-bold',
                    'placeholder':'masukkan alamat',
                    'required':'required'
                }
            )
        }

class FormMyDonation(forms.ModelForm):
    class Meta:
        model = MyDonation
        fields = [
            'donation','initial','nilai','email','bukti','keterangan'
        ]

        widgets = {
            'donation':forms.TextInput(
                attrs={
                'class':'form-control fs-6 fw-bold',
                'placeholder':'Masukkan Nama Lengkap',
                'minlength':5,
                'readonly':'readonly'
                }
            ),
            'initial':forms.TextInput(
                attrs={
                    'class':'form-control fs-6 fst-italic',
                    'placeholder':'Masukkan Nama Lengkap',
                    'minlength':5,
                    'required':'required'
                }
            ),
            'nilai':forms.NumberInput(
                attrs={
                    'class':'form-control fs-6 fst-italic',
                    'placeholder':'Masukkan Nilai',
                    'min':0,
                    'required':'required',
                    'value':0
                }
            ),
            'email': forms.EmailInput(
                attrs={
                    'class':'form-control fs-6 fst-italic',
                    'placeholder':'Masukkan Email',
                    'minlength':10,
                    'required':'required'
                }
            ),
            'bukti': forms.FileInput(
                attrs={
                    'class':'form-control fs-6 fst-italic',
                    'placeholder':'bukti transfer',
                    'required':'required',
                    'accept':'.gif,.jpg,.jpeg,.webp,.png'
                }
            ),
            'keterangan': forms.TextInput(
                attrs={
                    'class':'form-control fs-6 fst-italic',
                    'placeholder':'Masukkan Berita Keterangan',
                    'minlength':10,
                    'required':'required'
                }
            )
        }

        labels = {
            'donation':'Nomor Bukti Donasi:',
            'initial': 'Nama Pemberi Donasi:',
            'nilai': 'Nilai Donasi:',
            'bukti':'Bukti Foto Donasi:',
            'keterangan':'Berita Keterangan:',
            'email':'Email (untuk konfirmasi):'
        }
