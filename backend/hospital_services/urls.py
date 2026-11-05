from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"theatres", views.OperatingTheatreViewSet, basename="theatre")
router.register(r"ot-bookings", views.OTBookingViewSet, basename="ot-booking")
router.register(r"ambulances", views.AmbulanceViewSet, basename="ambulance")
router.register(r"ambulance-trips", views.AmbulanceTripViewSet, basename="ambulance-trip")
router.register(r"mortuary", views.MortuaryRecordViewSet, basename="mortuary")
router.register(r"sterile-sets", views.SterileSetViewSet, basename="sterile-set")
router.register(r"sterilization-cycles", views.SterilizationCycleViewSet, basename="sterilization-cycle")
router.register(r"laundry", views.LaundryBatchViewSet, basename="laundry")
router.register(r"leave", views.LeaveRequestViewSet, basename="leave")
router.register(r"feedback", views.PatientFeedbackViewSet, basename="feedback")
router.register(r"templates", views.TextTemplateViewSet, basename="text-template")

urlpatterns = [path("", include(router.urls))]
