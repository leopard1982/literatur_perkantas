from django.shortcuts import render
from django.conf import settings
from django.core.mail import send_mail

# Create your views here.
def mainPage(request):
    print(settings.EMAIL_PORT)
    # send_mail('Subject here Test', 'Here is the message. Test', 'adhy.chandra@live.co.uk', ['adhy.chandra@gmail.com'], fail_silently=False)
    return render(request,'index.html')