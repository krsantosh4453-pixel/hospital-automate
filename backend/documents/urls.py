"""
Documents API URLs for Hospital Management System.

Provides document management endpoints for patient documents, medical reports, etc.
"""

from django.urls import path
from . import views

app_name = 'documents'

# Literal paths come before '<id>/' so they are not read as document ids.
urlpatterns = [
    path('', views.DocumentListView.as_view(), name='document-list'),
    path('categories/', views.DocumentCategoryListView.as_view(), name='document-categories'),
    path('categories/<str:id>/', views.DocumentCategoryDetailView.as_view(), name='document-category-detail'),
    path('search/', views.DocumentSearchView.as_view(), name='document-search'),
    path('patient/<str:patient_id>/', views.PatientDocumentListView.as_view(), name='patient-documents'),
    path('patient/<str:patient_id>/upload/', views.PatientDocumentUploadView.as_view(), name='patient-document-upload'),
    path('<int:id>/', views.DocumentDetailView.as_view(), name='document-detail'),
    path('<int:id>/download/', views.DocumentDownloadView.as_view(), name='document-download'),
    path('<int:id>/preview/', views.DocumentPreviewView.as_view(), name='document-preview'),
]
