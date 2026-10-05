"""
Consent API URLs for Hospital Management System.

Provides consent form and record management endpoints.
"""

from django.urls import path
from . import views

app_name = 'consent'

urlpatterns = [
    # Consent Forms (templates)
    path('forms/', views.ConsentFormListView.as_view(), name='consent-form-list'),
    path('forms/<str:id>/', views.ConsentFormDetailView.as_view(), name='consent-form-detail'),
    path('forms/create/', views.ConsentFormCreateView.as_view(), name='consent-form-create'),

    # Consent Records (patient signatures)
    path('records/', views.ConsentRecordListView.as_view(), name='consent-record-list'),
    path('records/<str:id>/', views.ConsentRecordDetailView.as_view(), name='consent-record-detail'),
    path('records/create/', views.ConsentRecordCreateView.as_view(), name='consent-record-create'),
    path('records/<str:id>/sign/', views.sign_consent, name='sign-consent'),
    path('records/<str:id>/revoke/', views.revoke_consent, name='revoke-consent'),
    path('records/<str:id>/verify/', views.verify_consent, name='verify-consent'),

    # Digital Signature
    path('signature/create/', views.create_signature, name='create-signature'),
    path('signature/verify/', views.verify_signature, name='verify-signature'),

    # Audit
    path('audit/', views.ConsentAuditView.as_view(), name='consent-audit'),
]