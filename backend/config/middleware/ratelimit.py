"""
Custom rate limiting middleware for Django.

Provides additional rate limiting beyond DRF throttling.
"""

import hashlib
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings

from config.api_paths import unversioned_path
from config.client_ip import client_ip

logger = logging.getLogger(__name__)


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware for sensitive endpoints.

    Works alongside DRF throttling for additional protection.
    """

    # Endpoint patterns and their limits (requests per window)
    RATE_LIMITS = {
        # Auth endpoints - strict limits
        # Staff sign-in (password, OTP start/verify/resend): 5/min per account, so a
        # whole hospital behind one NAT address can sign in at shift change; the
        # per-IP ceiling still stops one address spraying many accounts. Failed
        # passwords also lock the account (users.security).
        '/api/auth/staff/login/': [
            {'limit': 5, 'window': 60, 'scope': 'account'},
            {'limit': 60, 'window': 60, 'scope': 'ip'},
        ],
        '/api/auth/token/refresh/': {'limit': 20, 'window': 60, 'scope': 'user'},
        '/api/auth/token/verify/': {'limit': 30, 'window': 60, 'scope': 'user'},
        '/api/auth/google/': {'limit': 5, 'window': 60, 'scope': 'ip'},
        # Patient codes: 5/min per phone or email, so patients sharing a mobile
        # carrier's address (carrier-grade NAT) are not blocked by each other
        # (P1-08); the per-IP ceiling still stops one address spraying numbers.
        '/api/auth/patient/otp/': [
            {'limit': 5, 'window': 60, 'scope': 'phone'},
            {'limit': 60, 'window': 60, 'scope': 'ip'},
        ],
        '/api/auth/patient/email-otp/': [
            {'limit': 5, 'window': 60, 'scope': 'email'},
            {'limit': 60, 'window': 60, 'scope': 'ip'},
        ],
        '/api/auth/patient/login/': {'limit': 5, 'window': 60, 'scope': 'ip'},
        '/api/auth/patient/token/': {'limit': 5, 'window': 60, 'scope': 'ip'},
        '/api/auth/proxy/': [
            {'limit': 5, 'window': 60, 'scope': 'phone'},
            {'limit': 60, 'window': 60, 'scope': 'ip'},
        ],
        '/api/auth/register/': {'limit': 5, 'window': 300, 'scope': 'ip'},
        '/api/auth/staff/logout/': {'limit': 30, 'window': 60, 'scope': 'user'},

        # OTP endpoints
        '/api/notifications/otp/': {'limit': 3, 'window': 60, 'scope': 'phone'},
        '/api/notifications/otp/verify/': {'limit': 5, 'window': 60, 'scope': 'phone'},

        # Password reset
        '/api/auth/password/reset/confirm/': {'limit': 5, 'window': 3600, 'scope': 'ip'},
        '/api/auth/password/reset/': {'limit': 3, 'window': 3600, 'scope': 'ip'},

        # AI endpoints - resource intensive
        '/api/ai/': {'limit': 30, 'window': 60, 'scope': 'user'},

        # Audio upload - large files
        '/api/ai/consultation/': {'limit': 10, 'window': 60, 'scope': 'user'},

        # FHIR endpoints
        '/api/fhir/': {'limit': 60, 'window': 60, 'scope': 'user'},

        # HL7 endpoints
        '/api/hl7/': {'limit': 60, 'window': 60, 'scope': 'ip'},

        # File upload endpoints
        '/api/patients/documents/': {'limit': 20, 'window': 60, 'scope': 'user'},
        '/api/documents/': {'limit': 20, 'window': 60, 'scope': 'user'},
    }

    def process_request(self, request):
        # Skip if rate limiting disabled
        if not getattr(settings, 'RATE_LIMIT_ENABLED', True):
            return None

        # Skip for health checks
        if request.path.startswith('/health/'):
            return None

        # Skip for static/media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None

        # The longest matching prefix wins, so a specific rule beats a broad one.
        # /api/v1/ paths match the same rules (and budgets) as /api/ ones.
        path = unversioned_path(request.path)
        matches = [pattern for pattern in self.RATE_LIMITS if path.startswith(pattern)]
        if not matches:
            return None
        matched_pattern = max(matches, key=len)
        rule = self.RATE_LIMITS[matched_pattern]
        # A rule is one budget or several; a request must fit within all of them.
        budgets = rule if isinstance(rule, list) else [rule]

        # One budget per rule and scope: paths under the same prefix share it
        counted = []
        for budget in budgets:
            scope = budget.get('scope', 'ip')
            key = self._rate_key(request, scope)
            cache_key = f"ratelimit:{scope}:{key}:{matched_pattern}"
            current = cache.get(cache_key, 0)
            if current >= budget['limit']:
                logger.warning(f"Rate limit exceeded: {scope} {key} for {request.path}")
                return JsonResponse({
                    'error': {
                        'code': 'RATE_LIMITED',
                        'message': f"Rate limit exceeded. Maximum {budget['limit']} requests per {budget['window']} seconds.",
                        'retry_after': budget['window'],
                    }
                }, status=429)
            counted.append((budget, cache_key, current))

        for budget, cache_key, current in counted:
            cache.set(cache_key, current + 1, budget['window'])

        # Headers report the first (tightest) budget; added in process_response
        budget, _, current = counted[0]
        request._rate_limit = {
            'limit': budget['limit'],
            'remaining': max(0, budget['limit'] - current - 1),
            'reset': int(time.time()) + budget['window'],
        }

        return None

    def _rate_key(self, request, scope):
        """The identity a budget counts against; the client IP when the request names none."""
        if scope == 'user' and request.user.is_authenticated:
            return f"user:{request.user.id}"
        if scope == 'phone':
            return self._extract_phone(request) or self._get_client_ip(request)
        if scope == 'email':
            return self._extract_email(request) or self._get_client_ip(request)
        if scope == 'account':
            return self._extract_account(request) or self._get_client_ip(request)
        return self._get_client_ip(request)

    def process_response(self, request, response):
        # Add rate limit headers if available
        if hasattr(request, '_rate_limit'):
            rl = request._rate_limit
            response['X-RateLimit-Limit'] = str(rl['limit'])
            response['X-RateLimit-Remaining'] = str(rl['remaining'])
            response['X-RateLimit-Reset'] = str(rl['reset'])

        return response

    def _get_client_ip(self, request):
        """Client IP; a spoofed X-Forwarded-For cannot rotate the limit key."""
        return client_ip(request) or 'unknown'

    def _extract_phone(self, request):
        """Extract phone number from request body."""
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                import json
                body = json.loads(request.body)
                return body.get('phone') or body.get('phone_number')
            except (json.JSONDecodeError, AttributeError):
                pass
        return None

    def _extract_account(self, request):
        """
        The staff account a sign-in step is for: the username or email typed
        (case-insensitive), or for the OTP steps the signed challenge, which
        belongs to one user. Hashed so the cache key holds no identifier.
        """
        if request.method not in ['POST', 'PUT', 'PATCH']:
            return None
        try:
            import json
            body = json.loads(request.body)
        except (json.JSONDecodeError, AttributeError, ValueError):
            return None
        if not isinstance(body, dict):
            return None
        name = str(body.get('username') or body.get('email') or '').strip().lower()
        value = f"name:{name}" if name else (f"challenge:{body['challenge']}" if body.get('challenge') else '')
        return hashlib.sha256(value.encode()).hexdigest()[:32] if value else None

    def _extract_email(self, request):
        """Extract email from request body."""
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                import json
                body = json.loads(request.body)
                return body.get('email')
            except (json.JSONDecodeError, AttributeError):
                pass
        return None

