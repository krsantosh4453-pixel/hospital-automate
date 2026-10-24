"""
Custom rate limiting middleware for Django.

Provides additional rate limiting beyond DRF throttling.
"""

import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware for sensitive endpoints.

    Works alongside DRF throttling for additional protection.
    """

    # Endpoint patterns and their limits (requests per window)
    RATE_LIMITS = {
        # Auth endpoints - strict limits
        '/api/auth/staff/login/': {'limit': 5, 'window': 60, 'scope': 'ip'},  # 5/min per IP
        '/api/auth/token/refresh/': {'limit': 20, 'window': 60, 'scope': 'user'},
        '/api/auth/token/verify/': {'limit': 30, 'window': 60, 'scope': 'user'},
        '/api/auth/google/': {'limit': 5, 'window': 60, 'scope': 'ip'},
        '/api/auth/patient/otp/': {'limit': 5, 'window': 60, 'scope': 'ip'},
        '/api/auth/patient/email-otp/': {'limit': 5, 'window': 60, 'scope': 'ip'},
        '/api/auth/patient/login/': {'limit': 5, 'window': 60, 'scope': 'ip'},
        '/api/auth/patient/token/': {'limit': 5, 'window': 60, 'scope': 'ip'},
        '/api/auth/register/': {'limit': 5, 'window': 300, 'scope': 'ip'},
        '/api/auth/staff/logout/': {'limit': 30, 'window': 60, 'scope': 'user'},

        # OTP endpoints
        '/api/notifications/otp/': {'limit': 3, 'window': 60, 'scope': 'phone'},
        '/api/notifications/otp/verify/': {'limit': 5, 'window': 60, 'scope': 'phone'},

        # Password reset
        # confirm is listed first: rules match by prefix in order.
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

        # Check if path matches any rate limit rule
        matched_rule = None
        for pattern, rule in self.RATE_LIMITS.items():
            if request.path.startswith(pattern):
                matched_rule = rule
                break

        if not matched_rule:
            return None

        # Determine rate limit key
        scope = matched_rule.get('scope', 'ip')
        limit = matched_rule['limit']
        window = matched_rule['window']

        if scope == 'ip':
            key = self._get_client_ip(request)
        elif scope == 'user':
            if request.user.is_authenticated:
                key = f"user:{request.user.id}"
            else:
                key = self._get_client_ip(request)
        elif scope == 'phone':
            # Extract phone from request body for OTP endpoints
            key = self._extract_phone(request) or self._get_client_ip(request)
        elif scope == 'email':
            key = self._extract_email(request) or self._get_client_ip(request)
        else:
            key = self._get_client_ip(request)

        cache_key = f"ratelimit:{scope}:{key}:{request.path}"

        # Check current count
        current = cache.get(cache_key, 0)

        if current >= limit:
            logger.warning(f"Rate limit exceeded: {key} for {request.path}")
            return JsonResponse({
                'error': {
                    'code': 'RATE_LIMITED',
                    'message': f'Rate limit exceeded. Maximum {limit} requests per {window} seconds.',
                    'retry_after': window,
                }
            }, status=429)

        # Increment counter
        cache.set(cache_key, current + 1, window)

        # Add rate limit headers to response (added in process_response)
        request._rate_limit = {
            'limit': limit,
            'remaining': max(0, limit - current - 1),
            'reset': int(time.time()) + window,
        }

        return None

    def process_response(self, request, response):
        # Add rate limit headers if available
        if hasattr(request, '_rate_limit'):
            rl = request._rate_limit
            response['X-RateLimit-Limit'] = str(rl['limit'])
            response['X-RateLimit-Remaining'] = str(rl['remaining'])
            response['X-RateLimit-Reset'] = str(rl['reset'])

        return response

    def _get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

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


class IPWhitelistMiddleware(MiddlewareMixin):
    """
    IP whitelist middleware for admin and sensitive endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Load from settings
        from django.conf import settings
        self.whitelist = getattr(settings, 'ADMIN_IP_WHITELIST', [])
        self.admin_paths = ['/admin/', '/api/admin/']

    def __call__(self, request):
        # Check if path requires IP whitelist
        if any(request.path.startswith(path) for path in self.admin_paths):
            client_ip = self._get_client_ip(request)
            if self.whitelist and client_ip not in self.whitelist:
                logger.warning(f"Blocked admin access from non-whitelisted IP: {client_ip}")
                return JsonResponse({
                    'error': {'code': 'FORBIDDEN', 'message': 'Access denied'}
                }, status=403)

        return self.get_response(request)

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')