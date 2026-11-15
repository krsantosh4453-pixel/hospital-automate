"""Consent API URLs (mounted at /api/consent/)."""

from django.urls import path

from . import rights, views

app_name = 'consent'

urlpatterns = [
    # P1-03 (DPDP Act): data-principal requests and the privacy notice.
    path('rights-requests/', rights.RightsRequestListView.as_view(), name='rights-request-list'),
    path('rights-requests/<int:id>/respond/', rights.RightsRequestRespondView.as_view(), name='rights-request-respond'),
    path('privacy-notice/', rights.PrivacyNoticeView.as_view(), name='privacy-notice'),
    path('forms/', views.ConsentFormListView.as_view(), name='consent-form-list'),
    path('forms/<str:id>/', views.ConsentFormDetailView.as_view(), name='consent-form-detail'),
    path('records/', views.ConsentRecordListView.as_view(), name='consent-record-list'),
    path('records/<int:id>/', views.ConsentRecordDetailView.as_view(), name='consent-record-detail'),
    path('records/<int:id>/revoke/', views.ConsentRecordRevokeView.as_view(), name='consent-record-revoke'),
    path('shares/', views.RecordShareListView.as_view(), name='record-share-list'),
    path('shares/received/', views.ReceivedShareListView.as_view(), name='record-share-received'),
    path('shares/<int:id>/revoke/', views.RecordShareRevokeView.as_view(), name='record-share-revoke'),
    path('shares/<int:id>/access-log/', views.RecordShareAccessLogView.as_view(), name='record-share-access-log'),
    path('shares/<int:id>/records/', views.SharedRecordsView.as_view(), name='record-share-records'),
]
