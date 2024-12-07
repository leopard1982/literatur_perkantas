from django.http import HttpResponseRedirect
from django.shortcuts import render, HttpResponse
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from .models import PageReview
from django.db.models import Avg

# Create your views here.
def mainPage(request):
    #get user id
    try:
        userid= request.GET['u']
    except:
        userid=None
    
    page_review = PageReview.objects.all().filter(is_active=True)
    print(page_review)
    
    context = {
        'page_review':page_review
    }

    # send_mail('Subject here Test', 'Here is the message. Test', 'adhy.chandra@live.co.uk', ['adhy.chandra@gmail.com'], fail_silently=False)
    return render(request,'index.html',context)