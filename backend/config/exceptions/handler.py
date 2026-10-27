"""
Custom exception handler for Django REST Framework.

Provides consistent error response format across the API.
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent error format.

    Format:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable message",
            "details": {}  # Optional additional details
        }
    }
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    # Get request info for logging
    request = context.get('request')
    request_id = getattr(request, 'request_id', None) if request else None
    user_id = getattr(request.user, 'id', None) if request and hasattr(request, 'user') else None

    # Log the exception
    log_extra = {
        'request_id': request_id,
        'user_id': user_id,
        'path': request.path if request else None,
        'method': request.method if request else None,
    }

    if response is not None:
        # DRF handled the exception
        logger.warning(
            f"API error: {exc.__class__.__name__}",
            extra=log_extra
        )

        # Format the response
        error_data = {
            'error': {
                'code': get_error_code(exc, response.status_code),
                'message': get_error_message(exc, response),
                'details': response.data if isinstance(response.data, dict) else {'detail': response.data},
            }
        }
        response.data = error_data
        return response

    # Unhandled exceptions
    logger.exception(
        f"Unhandled exception: {exc.__class__.__name__}",
        extra=log_extra
    )

    # Return generic error response
    if isinstance(exc, Http404):
        return Response(
            {'error': {'code': 'NOT_FOUND', 'message': 'Resource not found'}},
            status=status.HTTP_404_NOT_FOUND
        )

    if isinstance(exc, DjangoValidationError):
        return Response(
            {'error': {'code': 'VALIDATION_ERROR', 'message': 'Validation failed', 'details': exc.message_dict}},
            status=status.HTTP_400_BAD_REQUEST
        )

    if isinstance(exc, IntegrityError):
        return Response(
            {'error': {'code': 'INTEGRITY_ERROR', 'message': 'Database integrity error'}},
            status=status.HTTP_409_CONFLICT
        )

    # Generic server error
    return Response(
        {'error': {'code': 'INTERNAL_ERROR', 'message': 'An internal server error occurred'}},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def get_error_code(exc, status_code: int) -> str:
    """Map exception and status code to error code."""
    error_codes = {
        400: 'BAD_REQUEST',
        401: 'UNAUTHORIZED',
        403: 'FORBIDDEN',
        404: 'NOT_FOUND',
        405: 'METHOD_NOT_ALLOWED',
        409: 'CONFLICT',
        415: 'UNSUPPORTED_MEDIA_TYPE',
        429: 'RATE_LIMITED',
        500: 'INTERNAL_ERROR',
    }
    return error_codes.get(status_code, 'ERROR')


def get_error_message(exc, response) -> str:
    """Extract human-readable error message."""
    if hasattr(exc, 'detail'):
        detail = exc.detail
        if isinstance(detail, dict):
            # Get first error message
            for key, value in detail.items():
                if isinstance(value, list) and value:
                    return f"{key}: {value[0]}"
                elif isinstance(value, str):
                    return f"{key}: {value}"
            return "Validation failed"
        elif isinstance(detail, list) and detail:
            return str(detail[0])
        return str(detail)

    # Fallback to response data
    if isinstance(response.data, dict):
        return response.data.get('detail', 'An error occurred')
    return str(response.data)