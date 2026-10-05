from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import NotFound

from .models import Patient, PatientDocument, PatientHospital
from .serializers import PatientSerializer, PatientHospitalSerializer
from users.viewsets import HospitalScopedViewSet
from users.permissions import (
    IsReceptionist,
    IsDoctor,
    IsNurse,
    IsAdmin,
    IsPatientReadOnly,
    IsLinkedPatient,
)


class PatientViewSet(HospitalScopedViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsReceptionist | IsDoctor | IsNurse | IsAdmin | IsPatientReadOnly]

    def get_permissions(self):
        if getattr(self, "action", None) in {"documents", "delete_document"}:
            return [(IsReceptionist | IsDoctor | IsNurse | IsAdmin | IsLinkedPatient)()]
        return super().get_permissions()

    def _document_payload(self, document):
        file_url = None
        if document.file:
            file_url = self.request.build_absolute_uri(document.file.url)
        return {
            "id": document.id,
            "patient": document.patient_id,
            "title": document.title,
            "folder": document.folder,
            "file": file_url,
            "uploaded_at": document.uploaded_at,
        }

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="documents",
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def documents(self, request, pk=None):
        patient = self.get_object()
        if request.method == "GET":
            rows = patient.documents.all().order_by("-uploaded_at")
            return Response([self._document_payload(row) for row in rows])

        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"error": "A file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        document = PatientDocument.objects.create(
            patient=patient,
            title=(request.data.get("title") or upload.name)[:150],
            folder=(request.data.get("folder") or "")[:100],
            file=upload,
        )
        return Response(self._document_payload(document), status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["delete"], url_path=r"documents/(?P<doc_id>[0-9]+)")
    def delete_document(self, request, doc_id=None):
        try:
            document = PatientDocument.objects.select_related("patient").get(pk=doc_id)
        except PatientDocument.DoesNotExist:
            raise NotFound("Document not found.")
        if not self.get_queryset().filter(pk=document.patient_id).exists():
            raise NotFound("Document not found.")
        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        queryset = super().get_queryset()

        # Additional filtering by hospital query param if provided
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            hospital_ids = [int(hospital_id)]
            queryset = queryset.filter(
                Q(hospital_id__in=hospital_ids)
                | Q(
                    hospital_memberships__hospital_id__in=hospital_ids,
                    hospital_memberships__is_active=True,
                )
            ).distinct()

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)


class PatientHospitalViewSet(HospitalScopedViewSet):
    queryset = PatientHospital.objects.all()
    serializer_class = PatientHospitalSerializer
    permission_classes = [IsReceptionist | IsAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        return queryset