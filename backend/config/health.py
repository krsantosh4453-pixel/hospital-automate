"""
Health check middleware and views.
"""

import time
import logging
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.core.cache import cache

logger = logging.getLogger(__name__)


class HealthCheckMiddleware:
    """
    Middleware to handle health check requests efficiently.

    Bypasses authentication and other middleware for health endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.health_paths = ['/health/', '/health/live/', '/health/ready/']

    def __call__(self, request):
        if request.path in self.health_paths:
            return self.health_check(request)
        return self.get_response(request)

    def health_check(self, request):
        """Handle health check requests."""
        if request.path == '/health/live/':
            return self.liveness_check(request)
        elif request.path == '/health/ready/':
            return self.readiness_check(request)
        else:
            return self.basic_health_check(request)

    def basic_health_check(self, request):
        """Basic health check - just confirms Django is running."""
        return JsonResponse({
            'status': 'healthy',
            'service': 'hms-backend',
        })

    def liveness_check(self, request):
        """
        Liveness check - confirms process is alive.

        Should NOT check dependencies. Used by orchestration systems
        to determine if process should be restarted.
        """
        return JsonResponse({
            'status': 'alive',
            'service': 'hms-backend',
        })

    def readiness_check(self, request):
        """
        Readiness check - confirms service can handle requests.

        Checks critical dependencies: database, cache, etc.
        Used by orchestration systems to determine if traffic should be routed.
        """
        checks = {}
        overall_healthy = True

        # Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
            checks['database'] = {'status': 'healthy'}
        except Exception as e:
            checks['database'] = {'status': 'unhealthy', 'error': str(e)}
            overall_healthy = False

        # Cache check
        try:
            cache.set('health_check', 'ok', 10)
            result = cache.get('health_check')
            if result == 'ok':
                checks['cache'] = {'status': 'healthy'}
            else:
                checks['cache'] = {'status': 'unhealthy', 'error': 'Cache read/write failed'}
                overall_healthy = False
        except Exception as e:
            checks['cache'] = {'status': 'unhealthy', 'error': str(e)}
            overall_healthy = False

        status_code = 200 if overall_healthy else 503
        return JsonResponse({
            'status': 'ready' if overall_healthy else 'not_ready',
            'service': 'hms-backend',
            'checks': checks,
        }, status=status_code)


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
        except Exception as e:
            checks['database'] = f'unhealthy: {e}'
            overall_healthy = False

        # Cache
        try:
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') == 'ok':
                checks['cache'] = 'healthy'
            else:
                checks['cache'] = 'unhealthy: read/write failed'
                overall_healthy = False
        except Exception as e:
            checks['cache'] = f'unhealthy: {e}'
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