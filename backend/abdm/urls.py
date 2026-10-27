"""
ABDM/ABHA API URLs for Hospital Management System.

Provides ABDM (Ayushman Bharat Digital Mission) integration endpoints.
"""

from django.urls import path
from . import views

app_name = 'abdm'

urlpatterns = [
    # Health ID (ABHA) Management
    path('health-id/', views.HealthIDView.as_view(), name='health-id'),
    path('health-id/<str:health_id>/', views.HealthIDDetailView.as_view(), name='health-id-detail'),
    path('health-id/verify/', views.verify_health_id, name='verify-health-id'),
    path('health-id/link/', views.link_health_id, name='link-health-id'),

    # Consent Management
    path('consent/', views.ConsentView.as_view(), name='consent'),
    path('consent/<str:consent_id>/', views.ConsentDetailView.as_view(), name='consent-detail'),
    path('consent/request/', views.request_consent, name='request-consent'),
    path('consent/grant/', views.grant_consent, name='grant-consent'),
    path('consent/revoke/', views.revoke_consent, name='revoke-consent'),

    # Health Records
    path('records/', views.HealthRecordsView.as_view(), name='health-records'),
    path('records/<str:record_id>/', views.HealthRecordDetailView.as_view(), name='health-record-detail'),
    path('records/share/', views.share_records, name='share-records'),

    # Registry
    path('registry/facility/', views.FacilityRegistryView.as_view(), name='facility-registry'),
    path('registry/facility/<str:facility_id>/', views.FacilityDetailView.as_view(), name='facility-detail'),
    path('registry/professional/', views.ProfessionalRegistryView.as_view(), name='professional-registry'),
    path('registry/professional/<str:professional_id>/', views.ProfessionalDetailView.as_view(), name='professional-detail'),

    # Gateway
    path('gateway/token/', views.gateway_token, name='gateway-token'),
    path('gateway/verify/', views.verify_gateway_token, name='verify-gateway-token'),
]