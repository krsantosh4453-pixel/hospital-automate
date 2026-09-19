from rest_framework import serializers
from .models import (
    Admission,
    BedAllocation,
    DischargePlan,
    DischargeSummary,
    DischargeNote,
)


class AdmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admission
        fields = "__all__"


class BedAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BedAllocation
        fields = "__all__"


class DischargePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = DischargePlan
        fields = "__all__"


class DischargeSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DischargeSummary
        fields = "__all__"


class DischargeNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DischargeNote
        fields = "__all__"