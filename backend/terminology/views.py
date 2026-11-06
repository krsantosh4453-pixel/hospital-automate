"""ICD-10 typeahead search for clinicians."""

from django.db.models import Case, IntegerField, Q, Value, When
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsStaffUser

from .models import ICD10Code, compact_code

MIN_QUERY_LENGTH = 2
DEFAULT_LIMIT = 15
MAX_LIMIT = 50


def search_icd10(query, limit=DEFAULT_LIMIT):
    """
    Codes whose code starts with ``query`` (dot optional) rank first, then
    descriptions starting with it, then descriptions containing every word.
    """
    text = " ".join(str(query or "").lower().split())
    if len(text) < MIN_QUERY_LENGTH:
        return []
    compact = compact_code(text)
    words_match = Q()
    for word in text.split()[:6]:
        words_match &= Q(search_text__contains=word)
    code_match = Q(code_compact__startswith=compact) if compact else Q(pk__in=[])
    rows = (
        ICD10Code.objects.filter(code_match | words_match)
        .annotate(rank=Case(
            When(code_match, then=Value(0)),
            When(search_text__startswith=text, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        ))
        .order_by("rank", "code_compact")
        .values("code", "description", "billable")
    )
    return list(rows[:limit])


class ICD10SearchView(APIView):
    """GET ?q=diab&limit=15 — ICD-10 codes for the diagnosis typeahead."""

    permission_classes = [IsAuthenticated, IsStaffUser]

    def get(self, request):
        try:
            limit = max(1, min(int(request.query_params.get("limit", DEFAULT_LIMIT)), MAX_LIMIT))
        except (TypeError, ValueError):
            limit = DEFAULT_LIMIT
        return Response({"results": search_icd10(request.query_params.get("q"), limit)})
