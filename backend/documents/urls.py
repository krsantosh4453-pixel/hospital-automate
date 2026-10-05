"""
Documents API URLs for Hospital Management System.

Provides document management endpoints for patient documents, medical reports, etc.
"""

from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # Document listing and upload
    path('', views.DocumentListView.as_view(), name='document-list'),
    path('<str:id>/', views.DocumentDetailView.as_view(), name='document-detail'),
    path('<str:id>/download/', views.document_download, name='document-download'),
    path('<str:id>/preview/', views.document_preview, name='document-preview'),

    # Patient documents
    path('patient/<str:patient_id>/', views.PatientDocumentListView.as_view(), name='patient-documents'),
    path('patient/<str:patient_id>/upload/', views.PatientDocumentUploadView.as_view(), name='patient-document-upload'),

    # Categories/Folders
    path('categories/', views.DocumentCategoryListView.as_view(), name='document-categories'),
    path('categories/<str:id>/', views.DocumentCategoryDetailView.as_view(), name='document-category-detail'),

    # Search
    path('search/', views.document_search, name='document-search'),
]