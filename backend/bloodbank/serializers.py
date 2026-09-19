from rest_framework import serializers
from .models import (
    BloodInventory,
    BloodRequest,
    BloodTransaction,
)


class BloodInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BloodInventory
        fields = "__all__"


class BloodRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloodRequest
        fields = "__all__"


class BloodTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloodTransaction
        fields = "__all__"