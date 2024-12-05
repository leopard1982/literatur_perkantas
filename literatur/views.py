from django.shortcuts import render
from django.conf import settings
from django.core.mail import send_mail

# Create your views here.
def mainPage(request):
    # send_mail('Subject here', 'Here is the message.', 'adhy.chandra@live.co.uk', ['adhy.chandra@gmail.com'], fail_silently=False)
    return render(request,'index.html')