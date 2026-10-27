"""
Custom views for configuration.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View


@method_decorator(csrf_exempt, name='dispatch')
class CsrfFailureView(View):
    """
    Custom CSRF failure view that returns JSON response.
    """

    def dispatch(self, request, *args, **kwargs):
        return JsonResponse({
            'error': {
                'code': 'CSRF_FAILURE',
                'message': 'CSRF verification failed. Please refresh the page and try again.',
            }
        }, status=403)


def csrf_failure(request, reason=""):
    """Function-based CSRF failure view for Django's CSRF_FAILURE_VIEW setting."""
    return JsonResponse({
        'error': {
            'code': 'CSRF_FAILURE',
            'message': 'CSRF verification failed. Please refresh the page and try again.',
            'reason': reason,
        }
    }, status=403)