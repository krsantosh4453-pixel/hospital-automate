"""
FHIR R4 read API URLs, mounted at /api/fhir/.

Resource types and their sources are listed in ``fhir/sources.py``.
"""

from django.urls import path, re_path

from . import views

app_name = 'fhir'

_TYPE = r"(?P<resource_type>[A-Z][A-Za-z]+)"
_ID = r"(?P<resource_id>[A-Za-z0-9\-.]{1,64})"

urlpatterns = [
    path('metadata', views.CapabilityStatementView.as_view(), name='capability-statement'),
    path('metadata/', views.CapabilityStatementView.as_view()),
    re_path(rf'^Patient/{_ID}/\$everything/?$', views.PatientEverythingView.as_view(), name='patient-everything'),
    re_path(rf'^{_TYPE}/{_ID}/?$', views.ResourceReadView.as_view(), name='resource-read'),
    re_path(rf'^{_TYPE}/?$', views.ResourceSearchView.as_view(), name='resource-search'),
]
