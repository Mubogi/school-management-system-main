"""
Notification URLs
"""
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # WhatsApp Queue
    path('whatsapp-queue/', views.whatsapp_queue_view, name='whatsapp_queue'),
    path('whatsapp/preview/', views.whatsapp_preview, name='whatsapp_preview'),
    
    # Email Queue
    path('email-queue/', views.email_queue_view, name='email_queue'),
    
    # Templates
    path('templates/', views.notification_templates_view, name='templates'),
]
