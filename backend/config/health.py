"""
Health check views: /health/, /health/live/, /health/ready/.

These are public, so failures are logged here and only a status word is returned.
"""

import logging
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.core.cache import cache

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class HealthCheckView(View):
    """
    Health check endpoint view.

    Provides /health/, /health/live/, /health/ready/ endpoints.
    """

    def get(self, request, *args, **kwargs):
        path = request.path

        if path.endswith('/live/'):
            return self.liveness(request)
        elif path.endswith('/ready/'):
            return self.readiness(request)
        else:
            return self.basic(request)

    def basic(self, request):
        return JsonResponse({
            'status': 'healthy',
            'service': 'hms-backend',
            'version': '1.0.0',
        })

    def liveness(self, request):
        return JsonResponse({
            'status': 'alive',
            'service': 'hms-backend',
        })

    def readiness(self, request):
        checks = {}
        overall_healthy = True

        # Database
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            checks['database'] = 'healthy'
        except Exception:
            logger.exception('Readiness: database check failed')
            checks['database'] = 'unhealthy'
            overall_healthy = False

        # Cache
        try:
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') == 'ok':
                checks['cache'] = 'healthy'
            else:
                logger.error('Readiness: cache read/write failed')
                checks['cache'] = 'unhealthy'
                overall_healthy = False
        except Exception:
            logger.exception('Readiness: cache check failed')
            checks['cache'] = 'unhealthy'
            overall_healthy = False

        # Redis (if configured separately)
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection('default')
            redis_conn.ping()
            checks['redis'] = 'healthy'
        except Exception:
            checks['redis'] = 'not_configured_or_unhealthy'

        # Celery (if configured)
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            if stats:
                checks['celery'] = 'healthy'
            else:
                checks['celery'] = 'no_workers'
        except Exception:
            checks['celery'] = 'not_configured_or_unhealthy'

        status_code = 200 if overall_healthy else 503
        return JsonResponse({
            'status': 'ready' if overall_healthy else 'not_ready',
            'service': 'hms-backend',
            'checks': checks,
        }, status=status_code)
