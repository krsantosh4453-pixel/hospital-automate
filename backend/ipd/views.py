from rest_framework import viewsets

from .models import (
    Admission,
    BedAllocation,
    DischargePlan,
    DischargeSummary,
    DischargeNote,
)

from .serializers import (
    AdmissionSerializer,
    BedAllocationSerializer,
    DischargePlanSerializer,
    DischargeSummarySerializer,
    DischargeNoteSerializer,
)


class AdmissionViewSet(viewsets.ModelViewSet):
    queryset = Admission.objects.all()
    serializer_class = AdmissionSerializer


class BedAllocationViewSet(viewsets.ModelViewSet):
    queryset = BedAllocation.objects.all()
    serializer_class = BedAllocationSerializer


class DischargePlanViewSet(viewsets.ModelViewSet):
    queryset = DischargePlan.objects.all()
    serializer_class = DischargePlanSerializer


class DischargeSummaryViewSet(viewsets.ModelViewSet):
    queryset = DischargeSummary.objects.all()
    serializer_class = DischargeSummarySerializer


class DischargeNoteViewSet(viewsets.ModelViewSet):
    queryset = DischargeNote.objects.all()
    serializer_class = DischargeNoteSerializer
