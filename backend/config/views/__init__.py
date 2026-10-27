"""Views package."""
from .csrf import csrf_failure, CsrfFailureView

__all__ = ['csrf_failure', 'CsrfFailureView']