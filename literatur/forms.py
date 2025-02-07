from django import forms
from .models import UserDetail

class FormUpdateProfile(forms.ModelForm):
    class Meta:
        model = UserDetail
        fields = ['nama_lengkap','birthday','photo','no_whatsapp','pekerjaan','alamat']

        widgets = {
            'nama_lengkap':forms.TextInput(attrs={
                'class':'form-control fs-6',
                'placeholder':'Masukkan Nama Lengkap',
                'minlength':5
            }),
            'birthday':forms.DateInput(
                attrs={
                    'type':'date',
                    'class':'form-control fs-6'
                }
            ),
            'photo':forms.FileInput(
                attrs={
                    'class':'form-control fs-6',
                    'accept':'image/*'
                }
            ),
            'no_whatsapp': forms.TextInput(
                attrs={
                    'type':'number',
                    'class':'form-control fs-6',
                    'placeholder':'Masukkan nomor whatsapp'
                }
            ),
            'pekerjaan': forms.TextInput(
                attrs={
                    'class':'form-control fs-6',
                    'placeholder':'masukkan pekerjaan'
                }
            ),
            'alamat': forms.TextInput(
                attrs={
                    'class':'form-control fs-6',
                    'placeholder':'masukkan alamat'
                }
            )
        }