"""
FHIR R4 API URLs for Hospital Management System.

Provides FHIR-compliant endpoints for healthcare interoperability.
"""

from django.urls import path
from . import views

app_name = 'fhir'

urlpatterns = [
    # Capability Statement
    path('metadata/', views.capability_statement, name='capability-statement'),

    # Patient Resources
    path('Patient/', views.PatientListView.as_view(), name='patient-list'),
    path('Patient/<str:id>/', views.PatientDetailView.as_view(), name='patient-detail'),
    path('Patient/<str:id>/$everything', views.patient_everything, name='patient-everything'),

    # Observation Resources (Vitals, Lab Results)
    path('Observation/', views.ObservationListView.as_view(), name='observation-list'),
    path('Observation/<str:id>/', views.ObservationDetailView.as_view(), name='observation-detail'),

    # Encounter Resources
    path('Encounter/', views.EncounterListView.as_view(), name='encounter-list'),
    path('Encounter/<str:id>/', views.EncounterDetailView.as_view(), name='encounter-detail'),

    # Condition Resources (Diagnoses)
    path('Condition/', views.ConditionListView.as_view(), name='condition-list'),
    path('Condition/<str:id>/', views.ConditionDetailView.as_view(), name='condition-detail'),

    # MedicationRequest Resources (Prescriptions)
    path('MedicationRequest/', views.MedicationRequestListView.as_view(), name='medicationrequest-list'),
    path('MedicationRequest/<str:id>/', views.MedicationRequestDetailView.as_view(), name='medicationrequest-detail'),

    # Procedure Resources
    path('Procedure/', views.ProcedureListView.as_view(), name='procedure-list'),
    path('Procedure/<str:id>/', views.ProcedureDetailView.as_view(), name='procedure-detail'),

    # DocumentReference Resources
    path('DocumentReference/', views.DocumentReferenceListView.as_view(), name='documentreference-list'),
    path('DocumentReference/<str:id>/', views.DocumentReferenceDetailView.as_view(), name='documentreference-detail'),

    # Organization (Hospital)
    path('Organization/', views.OrganizationListView.as_view(), name='organization-list'),
    path('Organization/<str:id>/', views.OrganizationDetailView.as_view(), name='organization-detail'),

    # Practitioner (Doctors/Nurses)
    path('Practitioner/', views.PractitionerListView.as_view(), name='practitioner-list'),
    path('Practitioner/<str:id>/', views.PractitionerDetailView.as_view(), name='practitioner-detail'),

    # Location (Wards/Rooms/Beds)
    path('Location/', views.LocationListView.as_view(), name='location-list'),
    path('Location/<str:id>/', views.LocationDetailView.as_view(), name='location-detail'),

    # Bundle (for transactions)
    path('Bundle/', views.BundleView.as_view(), name='bundle'),

    # Search/Filter endpoints
    path('search/', views.search_resources, name='search-resources'),
]