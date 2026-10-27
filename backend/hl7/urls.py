"""
HL7 v2 API URLs for Hospital Management System.

Provides HL7 v2 messaging endpoints for healthcare integration.
"""

from django.urls import path
from . import views

app_name = 'hl7'

urlpatterns = [
    # Message receiving endpoints
    path('adt/', views.adt_endpoint, name='adt-endpoint'),
    path('orm/', views.orm_endpoint, name='orm-endpoint'),
    path('oru/', views.oru_endpoint, name='oru-endpoint'),
    path('mfn/', views.mfn_endpoint, name='mfn-endpoint'),

    # Generic message endpoint
    path('message/', views.hl7_message_endpoint, name='hl7-message'),

    # Acknowledgment
    path('ack/<str:message_id>/', views.acknowledgment, name='acknowledgment'),

    # Status
    path('status/', views.hl7_status, name='hl7-status'),
]