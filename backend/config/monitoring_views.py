"""
Monitoring views for Hospital Management System.

Provides Prometheus metrics and health check endpoints.
"""

from django.http import HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from config.monitoring import metrics_view, get_system_metrics, check_database_health, check_redis_health, check_celery_health


@method_decorator(csrf_exempt, name='dispatch')
class MetricsView(View):
    """Prometheus metrics endpoint."""

    def get(self, request):
        return metrics_view(request)


@method_decorator(csrf_exempt, name='dispatch')
class SystemMetricsView(View):
    """System metrics endpoint."""

    def get(self, request):
        return HttpResponse(
            content=get_system_metrics().__str__(),
            content_type='application/json'
        )