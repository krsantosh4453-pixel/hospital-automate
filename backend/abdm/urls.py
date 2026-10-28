"""
ABDM / ABHA URLs, mounted at /api/abdm/. See abdm/views.py for the flow.
"""

from django.urls import path

from . import views

app_name = 'abdm'

urlpatterns = [
    path('status/', views.StatusView.as_view(), name='status'),
    path('abha/request-otp/', views.RequestOTPView.as_view(), name='abha-request-otp'),
    path('abha/confirm-otp/', views.ConfirmOTPView.as_view(), name='abha-confirm-otp'),
    path('abha/links/', views.LinkListView.as_view(), name='abha-links'),
]
