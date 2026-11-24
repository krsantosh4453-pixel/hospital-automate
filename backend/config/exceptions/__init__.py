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
    """
    A human-readable message from DRF error data.

    Nested errors (a list of lines, each with its own field errors) are
    flattened into sentences with a readable place ("Line 1, quantity: ...").
    Never ``str()`` of a dict or list: that printed Python reprs such as
    ``ErrorDetail(string=..., code=...)`` to users (Prompt 4, BUG-007).
    """
    if isinstance(data, dict):
        for key in ("detail", "message"):
            if key in data and isinstance(data[key], str):
                return str(data[key])
    sentences = [_label(path, text) for path, text in _flatten(data, [])]
    return "; ".join(sentences) if sentences else "The request could not be completed."


_UNLABELLED = {"detail", "message", "non_field_errors", "__all__"}


def _flatten(value, path):
    """(path, text) for every leaf message in nested dicts and lists."""
    if isinstance(value, dict):
        for key, inner in value.items():
            yield from _flatten(inner, path + [key])
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            if isinstance(item, (dict, list, tuple)):
                yield from _flatten(item, path + [index])
            else:
                yield path, str(item)
    elif value not in (None, ""):
        yield path, str(value)


def _label(path, text):
    """'Line 1, quantity: text' for ['lines', 0, 'quantity']."""
    parts = []
    for part in path:
        is_index = isinstance(part, int) or (isinstance(part, str) and part.isdigit())
        if is_index:
            field = parts.pop() if parts else "item"
            name = field[:-1] if field.endswith("s") and len(field) > 1 else field
            parts.append(f"{name.capitalize()} {int(part) + 1}")
        elif str(part) not in _UNLABELLED:
            parts.append(str(part))
    return f"{', '.join(parts)}: {text}" if parts else text
