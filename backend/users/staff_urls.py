from django.urls import path

from .staff_admin import StaffApproveView, StaffListView, StaffMembershipView

urlpatterns = [
    path("", StaffListView.as_view(), name="staff-list"),
    path("<int:user_id>/approve/", StaffApproveView.as_view(), name="staff-approve"),
    path("<int:user_id>/membership/", StaffMembershipView.as_view(), name="staff-membership"),
]
