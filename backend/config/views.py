from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def csrf_failure(request, reason=""):
    """Custom CSRF failure view."""
    return render(request, 'csrf_failure.html', {'reason': reason}, status=403)
