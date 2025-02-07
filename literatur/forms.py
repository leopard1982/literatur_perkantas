from django import forms
from .models import UserDetail

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