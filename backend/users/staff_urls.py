from django.urls import path

from .staff_admin import StaffListView, StaffMembershipView
from .staff_invite import StaffInviteResendView, StaffInviteView

urlpatterns = [
    path("", StaffListView.as_view(), name="staff-list"),
    path("invite/", StaffInviteView.as_view(), name="staff-invite"),
    path("<int:user_id>/invite/", StaffInviteResendView.as_view(), name="staff-invite-resend"),
    path("<int:user_id>/membership/", StaffMembershipView.as_view(), name="staff-membership"),
]
