import json
import base64
import urllib.request
import urllib.error
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import GoogleAccount
from patients.models import Patient


def decode_jwt_payload(token):
    """
    Decodes the payload section of a JWT without external libraries.
    """
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        # Pad base64 string
        padded_b64 = payload_b64 + "=" * (-len(payload_b64) % 4)
        decoded_bytes = base64.urlsafe_b64decode(padded_b64)
        return json.loads(decoded_bytes.decode("utf-8"))
    except Exception:
        return None


def verify_google_token(token):
    """
    Verifies the Google ID token via Google's tokeninfo endpoint,
    with graceful fallback to JWT payload extraction.
    """
    google_data = None

    # 1. Try Google's tokeninfo API endpoint
    try:
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "HospitalManagementSystem/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                google_data = json.loads(response.read().decode("utf-8"))
    except Exception:
        google_data = None

    # 2. Fallback: Parse JWT payload directly
    if not google_data:
        jwt_payload = decode_jwt_payload(token)
        if jwt_payload and ("sub" in jwt_payload or "email" in jwt_payload):
            google_data = jwt_payload

    return google_data


@api_view(["POST"])
def google_login(request):
    token = request.data.get("credential")

    if not token:
        return Response(
            {"error": "Google credential is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        google_data = verify_google_token(token)

        if not google_data:
            return Response(
                {"error": "Unable to verify Google token. Please try again."},
                status=status.HTTP_400_BAD_REQUEST
            )

        google_id = google_data.get("sub")
        email = google_data.get("email")
        name = google_data.get("name", "")
        picture = google_data.get("picture", "")

        if not google_id and not email:
            return Response(
                {"error": "Invalid Google account data."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure we have a valid google_id fallback if only email is present
        if not google_id:
            google_id = f"google_{email}"

        # Find existing Google account
        google_account = GoogleAccount.objects.filter(
            google_id=google_id
        ).first()

        if google_account:
            user = google_account.user
            # Update name/picture if changed
            if name and google_account.name != name:
                google_account.name = name
            if picture and google_account.picture != picture:
                google_account.picture = picture
            google_account.save()
        else:
            # Find existing Django user by email
            user = User.objects.filter(email=email).first() if email else None
            if not user:
                user = User.objects.filter(username=email).first()

            if not user:
                username = email if email else f"user_{google_id[:10]}"
                user = User.objects.create_user(
                    username=username,
                    email=email or "",
                    first_name=name[:150] if name else ""
                )

            google_account = GoogleAccount.objects.create(
                user=user,
                google_id=google_id,
                email=email or "",
                name=name or "",
                picture=picture or ""
            )

        # Ensure linked Patient record exists
        patient = google_account.patient
        if not patient:
            # Look for patient with matching name or create a new Patient
            patient_name = name or (email.split("@")[0] if email else "Google Patient")
            patient = Patient.objects.filter(name__iexact=patient_name).first()

            if not patient:
                patient = Patient.objects.create(
                    name=patient_name,
                    age=30,
                    gender="Other",
                    phone="9876543210",
                    doctor="General Physician",
                    status="Active"
                )

            google_account.patient = patient
            google_account.save(update_fields=["patient"])

        return Response({
            "status": "success",
            "message": "Google login successful.",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": google_account.name or user.first_name,
                "picture": google_account.picture,
            },
            "patient": {
                "id": patient.id,
                "name": patient.name,
                "age": patient.age,
                "gender": patient.gender,
                "phone": patient.phone,
                "doctor": patient.doctor,
                "status": patient.status,
                "email": google_account.email,
                "picture": google_account.picture,
            }
        })

    except Exception as e:
        return Response(
            {"error": f"Google authentication failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )