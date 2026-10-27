"""
Request correlation ID middleware.

Adds a unique request ID to each request for tracing across services.
"""

import uuid
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

# Header names for correlation ID
CORRELATION_ID_HEADER = 'X-Request-ID'
CORRELATION_ID_RESPONSE_HEADER = 'X-Request-ID'


class CorrelationIdMiddleware(MiddlewareMixin):
    """
    Middleware to add correlation ID to requests.

    - Reads X-Request-ID from incoming request headers
    - Generates new UUID if not present
    - Adds to request object for use in views
    - Adds to response headers for client tracking
    - Adds to log records via logging filter
    """

    def process_request(self, request):
        # Get or generate correlation ID
        correlation_id = request.META.get('HTTP_X_REQUEST_ID')
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store on request object
        request.request_id = correlation_id

        # Add to META for logging filter
        request.META['REQUEST_ID'] = correlation_id

        return None

    def process_response(self, request, response):
        # Add correlation ID to response headers
        correlation_id = getattr(request, 'request_id', None)
        if correlation_id:
            response[CORRELATION_ID_RESPONSE_HEADER] = correlation_id
        return response


class LoggingContextMiddleware(MiddlewareMixin):
    """
    Middleware to add request context to log records.

    Adds request_id, user_id, hospital_id, path, method, status_code, duration_ms
    to log records for structured logging.
    """

    def process_request(self, request):
        # Store start time for duration calculation
        import time
        request._log_start_time = time.time()
        return None

    def process_response(self, request, response):
        # Calculate duration
        import time
        duration_ms = None
        if hasattr(request, '_log_start_time'):
            duration_ms = int((time.time() - request._log_start_time) * 1000)

        # Add context to response for logging
        request._log_context = {
            'request_id': getattr(request, 'request_id', None),
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
            'hospital_id': getattr(request, 'hospital_id', None),
            'path': request.path,
            'method': request.method,
            'status_code': response.status_code,
            'duration_ms': duration_ms,
        }
        return response


def get_request_context(request) -> dict:
    """Extract request context for logging."""
    return getattr(request, '_log_context', {})