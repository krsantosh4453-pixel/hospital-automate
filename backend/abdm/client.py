"""
ABDM gateway and ABHA (v3) HTTP client.

Covers milestone M1 "verify an existing ABHA and link it to a patient":
gateway session token, ABHA public key, OTP request and OTP verification.
Health-record sharing (M2/M3: HIP callbacks, consent artefacts, Fidelius
encryption) is not built and needs ABDM certification first.

PATHS come from the ABDM ABHA v3 sandbox documentation. Confirm them, and the
response field names in ``_account_from``, against the sandbox once
credentials are issued; they are the only places to change.
"""

import base64
import logging
import uuid
from datetime import datetime, timezone

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

PATHS = {
    "session": "/api/hiecm/gateway/v3/sessions",          # on ABDM_BASE_URL
    "public_key": "/v3/profile/public/certificate",       # on ABDM_ABHA_BASE_URL
    "login_request_otp": "/v3/profile/login/request/otp",
    "login_verify": "/v3/profile/login/verify",
}

OTP_SCOPES = {
    # OTP sent to the mobile number registered with Aadhaar
    "aadhaar": ["abha-login", "aadhaar-verify"],
    # OTP sent to the mobile number registered with ABHA
    "abdm": ["abha-login", "mobile-verify"],
}

REQUEST_TIMEOUT_SECONDS = 30
TOKEN_CACHE_KEY = "abdm:gateway-token"
PUBLIC_KEY_CACHE_KEY = "abdm:abha-public-key"
PUBLIC_KEY_CACHE_SECONDS = 6 * 60 * 60
TOKEN_EXPIRY_MARGIN_SECONDS = 60


class ABDMNotConfigured(Exception):
    """ABDM is switched off or the sandbox/production credentials are missing."""


class ABDMError(Exception):
    """A call to ABDM failed; ``str(exc)`` is safe to show to staff."""


def is_configured():
    return bool(
        getattr(settings, "ABDM_ENABLED", False)
        and getattr(settings, "ABDM_BASE_URL", None)
        and getattr(settings, "ABDM_ABHA_BASE_URL", None)
        and getattr(settings, "ABDM_CLIENT_ID", None)
        and getattr(settings, "ABDM_CLIENT_SECRET", None)
    )


def digits(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


class ABDMClient:
    def __init__(self):
        if not is_configured():
            raise ABDMNotConfigured(
                "ABDM is not configured. Set ABDM_CLIENT_ID and ABDM_CLIENT_SECRET from the ABDM sandbox."
            )
        self.gateway_url = settings.ABDM_BASE_URL.rstrip("/")
        self.abha_url = settings.ABDM_ABHA_BASE_URL.rstrip("/")
        self.cm_id = getattr(settings, "ABDM_CM_ID", "sbx")

    # Transport -----------------------------------------------------------

    def _headers(self, with_token=True):
        headers = {
            "Content-Type": "application/json",
            "REQUEST-ID": str(uuid.uuid4()),
            "TIMESTAMP": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "X-CM-ID": self.cm_id,
        }
        if with_token:
            headers["Authorization"] = f"Bearer {self.gateway_token()}"
        return headers

    def _call(self, method, url, *, with_token=True, payload=None):
        try:
            response = requests.request(
                method, url, json=payload, headers=self._headers(with_token), timeout=REQUEST_TIMEOUT_SECONDS
            )
        except requests.RequestException as exc:
            logger.error("ABDM %s %s failed: %s", method, url, type(exc).__name__)
            raise ABDMError("Could not reach ABDM. Try again shortly.") from exc
        if response.status_code >= 400:
            # ABDM error bodies can echo identifiers; log only the status.
            logger.error("ABDM %s %s returned HTTP %s", method, url, response.status_code)
            if response.status_code in (401, 403):
                raise ABDMError("ABDM rejected the hospital's credentials.")
            if response.status_code == 400:
                raise ABDMError("ABDM did not accept the details. Check the ABHA number or OTP.")
            raise ABDMError(f"ABDM returned HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError as exc:
            raise ABDMError("ABDM returned an unreadable response.") from exc

    # Session and encryption ----------------------------------------------

    def gateway_token(self):
        token = cache.get(TOKEN_CACHE_KEY)
        if token:
            return token
        body = self._call("POST", self.gateway_url + PATHS["session"], with_token=False, payload={
            "clientId": settings.ABDM_CLIENT_ID,
            "clientSecret": settings.ABDM_CLIENT_SECRET,
            "grantType": "client_credentials",
        })
        token = body.get("accessToken")
        if not token:
            raise ABDMError("ABDM did not return a session token.")
        lifetime = int(body.get("expiresIn") or 600) - TOKEN_EXPIRY_MARGIN_SECONDS
        cache.set(TOKEN_CACHE_KEY, token, max(lifetime, 60))
        return token

    def public_key(self):
        pem = cache.get(PUBLIC_KEY_CACHE_KEY)
        if not pem:
            body = self._call("GET", self.abha_url + PATHS["public_key"])
            pem = body.get("publicKey")
            if not pem:
                raise ABDMError("ABDM did not return its encryption key.")
            cache.set(PUBLIC_KEY_CACHE_KEY, pem, PUBLIC_KEY_CACHE_SECONDS)
        return pem

    def encrypt(self, text):
        """RSA/ECB/OAEPWithSHA-1AndMGF1Padding, as ABHA v3 requires for identifiers and OTPs."""
        key_text = self.public_key().strip()
        if "BEGIN" in key_text:
            key = serialization.load_pem_public_key(key_text.encode())
        else:
            key = serialization.load_der_public_key(base64.b64decode(key_text))
        cipher = key.encrypt(
            str(text).encode(),
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA1()), algorithm=hashes.SHA1(), label=None),
        )
        return base64.b64encode(cipher).decode()

    # ABHA login (verify an existing ABHA) ----------------------------------

    def request_login_otp(self, abha_number, otp_system):
        """Send an OTP for ``abha_number``; returns ABDM's transaction id."""
        body = self._call("POST", self.abha_url + PATHS["login_request_otp"], payload={
            "scope": OTP_SCOPES[otp_system],
            "loginHint": "abha-number",
            "loginId": self.encrypt(abha_number),
            "otpSystem": otp_system,
        })
        txn_id = body.get("txnId")
        if not txn_id:
            raise ABDMError("ABDM did not start the OTP check.")
        return txn_id

    def verify_login_otp(self, txn_id, otp, otp_system):
        """Check the OTP; returns the verified ABHA account as a plain dict."""
        body = self._call("POST", self.abha_url + PATHS["login_verify"], payload={
            "scope": OTP_SCOPES[otp_system],
            "authData": {"authMethods": ["otp"], "otp": {"txnId": txn_id, "otpValue": self.encrypt(otp)}},
        })
        if str(body.get("authResult", "")).lower() != "success":
            raise ABDMError("The OTP was not accepted.")
        return self._account_from(body)

    @staticmethod
    def _account_from(body):
        accounts = body.get("accounts") or []
        if not accounts:
            raise ABDMError("ABDM did not return the ABHA account.")
        account = accounts[0]
        return {
            "abha_number": account.get("ABHANumber", ""),
            "abha_address": account.get("preferredAbhaAddress", ""),
            "name": account.get("name", ""),
            "gender": account.get("gender", ""),
            "year_of_birth": account.get("yearOfBirth", ""),
        }
