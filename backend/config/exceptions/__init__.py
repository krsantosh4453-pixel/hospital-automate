from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for consistent error responses.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Add standard error structure
        custom_response = {
            'error': True,
            'status_code': response.status_code,
            'message': _get_error_message(response.data),
            'details': response.data,
        }
        response.data = custom_response
        
        # Log the error
        logger.warning(
            f"API Error: {response.status_code} - {custom_response['message']}",
            extra={
                'status_code': response.status_code,
                'path': context.get('request').path if context.get('request') else None,
                'method': context.get('request').method if context.get('request') else None,
            }
        )

    return response


def _get_error_message(data):
    """Extract a human-readable error message from response data."""
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        if 'message' in data:
            return str(data['message'])
        # For validation errors, return field-specific messages
        messages = []
        for field, errors in data.items():
            if isinstance(errors, list):
                for error in errors:
                    messages.append(f"{field}: {error}")
            else:
                messages.append(f"{field}: {errors}")
        if messages:
            return "; ".join(messages)
    elif isinstance(data, list):
        return "; ".join(str(item) for item in data)
    return str(data)
