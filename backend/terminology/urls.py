"""Terminology API URLs (mounted at /api/terminology/)."""

from django.urls import path

from . import views

app_name = "terminology"

urlpatterns = [
    path("icd10/", views.ICD10SearchView.as_view(), name="icd10-search"),
]
