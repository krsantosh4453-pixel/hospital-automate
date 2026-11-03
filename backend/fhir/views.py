"""
FHIR R4 read API for Hospital Management System.

Read-only and hospital-scoped: a client acts in one hospital (``X-Hospital-ID``
header or ``?hospital=``) and must hold the Admin role there, because this is
a bulk export interface for integrations, not a clinician screen. Every read
is written to the audit log. Errors come back as FHIR OperationOutcome.

Supported: ``GET metadata``, ``GET {type}`` (search), ``GET {type}/{id}``
(read) and ``GET Patient/{id}/$everything``. Search parameters: ``patient``
(or ``subject``), ``_count``, ``_offset``; for Patient also ``name`` and
``identifier`` (UHID). ``_count`` counts internal records, so an Observation
page can hold several resources per vital-sign reading.
"""

import logging
import re

from django.conf import settings
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_audit
from interoperability.fhir.mappings.base import MappingContext
from interoperability.fhir.resources.base import FHIRBundleBuilder
from users.models import StaffRole
from users.permissions import IsAdmin, get_request_hospital_id, get_user_hospital_ids, get_user_roles

from .sources import PATIENT_COMPARTMENT, RESOURCES

logger = logging.getLogger(__name__)

FHIR_JSON = "application/fhir+json"
FHIR_VERSION = "4.0.1"
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
# Patient/$everything returns at most this many records per resource type;
# beyond that the bundle carries a warning and the client pages per type.
EVERYTHING_LIMIT_PER_TYPE = 500

_RESOURCE_ID = re.compile(r"^[A-Za-z0-9\-.]{1,64}$")
_TRAILING_PK = re.compile(r"-(\d+)$")
_PATIENT_REF = re.compile(r"^(?:Patient/)?(?:Patient-)?(\d+)$")


def _outcome(status_code, code, diagnostics, severity="error"):
    return Response(
        {"resourceType": "OperationOutcome",
         "issue": [{"severity": severity, "code": code, "diagnostics": diagnostics}]},
        status=status_code,
        content_type=FHIR_JSON,
    )


def _issue_code(status_code):
    return {400: "invalid", 401: "login", 403: "forbidden", 404: "not-found", 429: "throttled"}.get(
        status_code, "exception"
    )


def _int_param(request, name, default, minimum, maximum):
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValidationError(f"{name} must be a whole number.")
    return max(minimum, min(value, maximum))


def _patient_pk(value):
    match = _PATIENT_REF.match(str(value or "").strip())
    if not match:
        raise ValidationError("patient must look like Patient/Patient-123, Patient-123 or 123.")
    return int(match.group(1))


def _resource_pk(resource_id):
    if not _RESOURCE_ID.match(resource_id or ""):
        return None
    match = _TRAILING_PK.search(resource_id)
    return int(match.group(1)) if match else None


def _as_list(mapped):
    items = mapped if isinstance(mapped, list) else [mapped]
    return [item for item in items if item]


class FHIRBaseView(APIView):
    permission_classes = [IsAdmin]
    throttle_scope = "fhir"
    hospital_id = None

    def check_permissions(self, request):
        if not getattr(settings, "FHIR_ENABLED", False):
            raise NotFound("The FHIR API is not enabled on this server.")
        super().check_permissions(request)
        self.hospital_id = self._acting_hospital(request)

    def _acting_hospital(self, request):
        hospital_id = get_request_hospital_id(request, self)
        if hospital_id is None:
            # Without a header, an admin of exactly one hospital acts there.
            admin_of = [h for h in get_user_hospital_ids(request.user)
                        if StaffRole.ADMIN in get_user_roles(request.user, h)]
            if len(admin_of) != 1:
                raise ValidationError("Send the X-Hospital-ID header to choose a hospital.")
            hospital_id = admin_of[0]
        if StaffRole.ADMIN not in get_user_roles(request.user, hospital_id):
            self.permission_denied(request, message="FHIR export needs the Admin role in this hospital.")
        return hospital_id

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if isinstance(response.data, dict) and response.data.get("resourceType") == "OperationOutcome":
            return response
        detail = getattr(exc, "detail", None) or response.data
        outcome = _outcome(response.status_code, _issue_code(response.status_code), str(detail))
        for header, value in response.items():
            outcome[header] = value
        outcome["Content-Type"] = FHIR_JSON
        return outcome

    # Helpers ---------------------------------------------------------------

    def context(self):
        return MappingContext(
            hospital_id=self.hospital_id,
            base_url=self.request.build_absolute_uri("/api/fhir").rstrip("/"),
            user_id=self.request.user.pk,
        )

    def sources_for(self, resource_type):
        sources = RESOURCES.get(resource_type)
        if sources is None:
            raise NotFound(f"Resource type '{resource_type}' is not supported.")
        return sources

    def map_rows(self, source, rows, context):
        mapper = source.mapper(context)
        return [resource for row in rows for resource in _as_list(mapper.map(row))]

    def respond(self, data, status_code=status.HTTP_200_OK):
        return Response(data, status=status_code, content_type=FHIR_JSON)

    def audit(self, action, details, patient=None):
        record_audit(self.request, action, obj=patient, hospital=self.hospital_id, details=details)


class CapabilityStatementView(FHIRBaseView):
    """GET metadata. Public, as the FHIR spec expects; lists what is served."""

    permission_classes = [AllowAny]

    def check_permissions(self, request):
        if not getattr(settings, "FHIR_ENABLED", False):
            raise NotFound("The FHIR API is not enabled on this server.")

    def get(self, request):
        common = [{"name": "patient", "type": "reference"},
                  {"name": "_count", "type": "number"},
                  {"name": "_offset", "type": "number"}]
        resources = []
        for name, sources in RESOURCES.items():
            params = common if all(s.patient_field for s in sources) else common[1:]
            if name == "Patient":
                params = [{"name": "name", "type": "string"},
                          {"name": "identifier", "type": "token"}] + common[1:]
            entry = {
                "type": name,
                "profile": f"http://hl7.org/fhir/StructureDefinition/{name}",
                "interaction": [{"code": "read"}, {"code": "search-type"}],
                "searchParam": params,
            }
            if name == "Patient":
                entry["operation"] = [{"name": "everything",
                                       "definition": "http://hl7.org/fhir/OperationDefinition/Patient-everything"}]
            resources.append(entry)
        return self.respond({
            "resourceType": "CapabilityStatement",
            "status": "active",
            "kind": "instance",
            "software": {"name": "Hospital Automate HMS"},
            "implementation": {"description": "Hospital Automate FHIR R4 read API",
                               "url": request.build_absolute_uri("/api/fhir/")},
            "fhirVersion": FHIR_VERSION,
            "format": ["json"],
            "rest": [{
                "mode": "server",
                "security": {"description": "JWT bearer token of a hospital Admin; send X-Hospital-ID."},
                "resource": resources,
            }],
        })


class ResourceSearchView(FHIRBaseView):
    """GET {type}?patient=&_count=&_offset= returns a searchset Bundle."""

    def get(self, request, resource_type):
        sources = self.sources_for(resource_type)
        count = _int_param(request, "_count", DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE)
        offset = _int_param(request, "_offset", 0, 0, 10**9)
        patient_ref = request.query_params.get("patient") or request.query_params.get("subject")
        patient_pk = _patient_pk(patient_ref) if patient_ref else None

        querysets = [(source, self._filtered(source, resource_type, patient_pk)) for source in sources]
        counts = [qs.count() for _, qs in querysets]
        total_rows = sum(counts)
        context = self.context()
        bundle = FHIRBundleBuilder(bundle_type="searchset")
        # Page across the sources as if their rows were one list.
        skip, room = offset, count
        for (source, qs), rows_in_source in zip(querysets, counts):
            if room <= 0:
                break
            if skip >= rows_in_source:
                skip -= rows_in_source
                continue
            rows = list(qs[skip:skip + room])
            skip = 0
            room -= len(rows)
            for resource in self.map_rows(source, rows, context):
                bundle.add_entry(resource, full_url=context.get_resource_url(resource_type, resource["id"]),
                                 search_mode="match")

        self._add_paging_links(bundle, request, offset, count, total_rows)
        self.audit("fhir.search", {"resource": resource_type, "patient": patient_pk,
                                   "offset": offset, "count": count, "returned": len(bundle.entries)})
        return self.respond(bundle.build())

    def _filtered(self, source, resource_type, patient_pk):
        qs = source.queryset(self.hospital_id)
        if patient_pk is not None:
            if not source.patient_field:
                return qs.none()
            qs = qs.filter(**{source.patient_field: patient_pk})
        if resource_type == "Patient":
            qs = self._patient_search(qs)
        return qs.order_by("-pk")

    def _patient_search(self, qs):
        name = (self.request.query_params.get("name") or "").strip()
        identifier = (self.request.query_params.get("identifier") or "").strip()
        if name:
            qs = qs.filter(name__icontains=name)
        if identifier:
            # Accept "system|value" as FHIR token syntax; only the value is matched.
            value = identifier.split("|")[-1]
            qs = qs.filter(hospital_memberships__hospital_id=self.hospital_id,
                           hospital_memberships__uhid__iexact=value)
        return qs

    def _add_paging_links(self, bundle, request, offset, count, total_rows):
        base = request.build_absolute_uri(request.path)

        def page_url(page_offset):
            params = request.query_params.copy()
            params["_offset"] = str(page_offset)
            params["_count"] = str(count)
            return f"{base}?{params.urlencode()}"

        bundle.add_link("self", page_url(offset))
        if offset + count < total_rows:
            bundle.add_link("next", page_url(offset + count))
        if offset > 0:
            bundle.add_link("previous", page_url(max(0, offset - count)))


class ResourceReadView(FHIRBaseView):
    """GET {type}/{id} returns one resource or a not-found OperationOutcome."""

    def get(self, request, resource_type, resource_id):
        resource, row = self.find(resource_type, resource_id)
        patient = row if resource_type == "Patient" else None
        self.audit("fhir.read", {"resource": resource_type, "id": resource_id}, patient=patient)
        return self.respond(resource)

    def find(self, resource_type, resource_id):
        sources = self.sources_for(resource_type)
        pk = _resource_pk(resource_id)
        if pk is not None:
            context = self.context()
            for source in sources:
                row = source.queryset(self.hospital_id).filter(**{source.id_lookup: pk}).first()
                if row is None:
                    continue
                for resource in self.map_rows(source, [row], context):
                    if resource.get("id") == resource_id:
                        return resource, row
        raise NotFound(f"{resource_type}/{resource_id} was not found in this hospital.")


class PatientEverythingView(ResourceReadView):
    """GET Patient/{id}/$everything returns the patient and everything linked to them."""

    def get(self, request, resource_id):
        patient_resource, patient = self.find("Patient", resource_id)
        context = self.context()
        bundle = FHIRBundleBuilder(bundle_type="searchset")
        bundle.add_entry(patient_resource, full_url=context.get_resource_url("Patient", resource_id),
                         search_mode="match")
        truncated = []
        for resource_type in PATIENT_COMPARTMENT:
            for source in RESOURCES[resource_type]:
                qs = source.queryset(self.hospital_id).filter(**{source.patient_field: patient.pk}).order_by("-pk")
                rows = list(qs[:EVERYTHING_LIMIT_PER_TYPE + 1])
                if len(rows) > EVERYTHING_LIMIT_PER_TYPE:
                    rows = rows[:EVERYTHING_LIMIT_PER_TYPE]
                    truncated.append(resource_type)
                for resource in self.map_rows(source, rows, context):
                    bundle.add_entry(resource, full_url=context.get_resource_url(resource_type, resource["id"]),
                                     search_mode="include")
        if truncated:
            note = (f"More than {EVERYTHING_LIMIT_PER_TYPE} records for: {', '.join(sorted(set(truncated)))}. "
                    "Page through GET {type}?patient=... for the rest.")
            logger.warning("FHIR $everything truncated for patient %s: %s", patient.pk, truncated)
            bundle.add_entry({"resourceType": "OperationOutcome",
                              "issue": [{"severity": "warning", "code": "too-costly", "diagnostics": note}]},
                             search_mode="outcome")
        self.audit("fhir.everything", {"resource": "Patient", "id": resource_id,
                                       "returned": len(bundle.entries), "truncated": truncated}, patient=patient)
        return self.respond(bundle.build())
