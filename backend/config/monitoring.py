"""
Monitoring and metrics integration for Hospital Management System.

Provides interfaces for Prometheus, Sentry, and custom metrics.
"""

import logging
import time
import functools
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse

logger = logging.getLogger(__name__)


# ============================================================
# Prometheus Metrics (if django-prometheus installed)
# ============================================================

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Histogram = Gauge = None

if PROMETHEUS_AVAILABLE:
    # Request metrics
    http_requests_total = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )

    http_request_duration_seconds = Histogram(
        'http_request_duration_seconds',
        'HTTP request duration in seconds',
        ['method', 'endpoint']
    )

    # Database metrics
    db_query_duration_seconds = Histogram(
        'db_query_duration_seconds',
        'Database query duration in seconds',
        ['query_type']
    )

    # Business metrics
    active_users = Gauge('active_users', 'Number of active users')
    active_patients = Gauge('active_patients', 'Number of active patients')
    appointments_today = Gauge('appointments_today', 'Appointments scheduled today')
    bed_occupancy = Gauge('bed_occupancy_percent', 'Bed occupancy percentage')

    # Celery metrics
    celery_tasks_total = Counter(
        'celery_tasks_total',
        'Total Celery tasks',
        ['task_name', 'status']
    )

    celery_task_duration_seconds = Histogram(
        'celery_task_duration_seconds',
        'Celery task duration in seconds',
        ['task_name']
    )


class PrometheusMiddleware(MiddlewareMixin):
    """Middleware to collect Prometheus metrics."""

    def process_request(self, request):
        request._prometheus_start_time = time.time()
        return None

    def process_response(self, request, response):
        if not PROMETHEUS_AVAILABLE:
            return response

        # Skip metrics endpoint
        if request.path in ['/metrics/', '/health/', '/health/live/', '/health/ready/']:
            return response

        duration = time.time() - request._prometheus_start_time

        # Normalize endpoint for cardinality control
        endpoint = self._normalize_endpoint(request.path)

        http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)

        return response

    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path to reduce cardinality."""
        # Replace IDs with placeholders
        import re
        path = re.sub(r'/\d+', '/{id}', path)
        path = re.sub(r'/[a-f0-9-]{36}', '/{uuid}', path)
        return path


def metrics_view(request):
    """Prometheus metrics endpoint."""
    if not PROMETHEUS_AVAILABLE:
        return HttpResponse('Prometheus client not installed', status=501)

    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)


# ============================================================
# Sentry Integration
# ============================================================

def init_sentry():
    """Initialize Sentry SDK."""
    if not getattr(settings, 'MONITORING_ENABLED', False):
        return

    sentry_dsn = getattr(settings, 'SENTRY_DSN', None)
    if not sentry_dsn:
        logger.info("SENTRY_DSN not configured, skipping Sentry initialization")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=getattr(settings, 'SENTRY_ENVIRONMENT', 'production'),
            integrations=[
                DjangoIntegration(
                    transaction_style='url',
                    middleware_spans=True,
                    signals_spans=True,
                ),
                CeleryIntegration(
                    monitor_beat_tasks=True,
                    propagate_traces=True,
                ),
                RedisIntegration(),
                sentry_logging,
            ],
            traces_sample_rate=getattr(settings, 'SENTRY_TRACES_SAMPLE_RATE', 0.1),
            profiles_sample_rate=getattr(settings, 'SENTRY_PROFILES_SAMPLE_RATE', 0.1),
            send_default_pii=False,  # Don't send PII
            max_breadcrumbs=50,
            attach_stacktrace=True,
        )

        logger.info("Sentry initialized successfully")

    except ImportError:
        logger.warning("sentry-sdk not installed, skipping Sentry initialization")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def capture_exception(exc, **context):
    """Capture exception to Sentry with context."""
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(exc)
    except ImportError:
        pass
    except Exception:
        pass


def capture_message(message, level='info', **context):
    """Capture message to Sentry."""
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    except ImportError:
        pass
    except Exception:
        pass


# ============================================================
# Custom Business Metrics
# ============================================================

class MetricsCollector:
    """Collects and exposes business metrics."""

    @staticmethod
    def collect_daily_metrics():
        """Collect daily business metrics."""
        try:
            import django
            django.setup()

            from patients.models import Patient
            from appointments.models import Appointment
            from hospital.models import Bed
            from django.utils import timezone

            today = timezone.now().date()

            if PROMETHEUS_AVAILABLE:
                active_users.count()
                active_patients.set(Patient.objects.filter(status='Active').count())
                appointments_today.set(
                    Appointment.objects.filter(appointment_date__date=today).count()
                )

                total_beds = Bed.objects.count()
                occupied_beds = Bed.objects.filter(status='Occupied').count()
                if total_beds > 0:
                    bed_occupancy.set((occupied_beds / total_beds) * 100)

        except Exception as e:
            logger.error(f"Failed to collect daily metrics: {e}")

    @staticmethod
    def record_celery_task(task_name: str, duration: float, success: bool):
        """Record Celery task metrics."""
        if PROMETHEUS_AVAILABLE:
            celery_tasks_total.labels(
                task_name=task_name,
                status='success' if success else 'failure'
            ).inc()
            celery_task_duration_seconds.labels(
                task_name=task_name
            ).observe(duration)


def monitor_task(task_name: str):
    """Decorator to monitor Celery task execution."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            success = False
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                capture_exception(e, task=task_name)
                raise
            finally:
                duration = time.time() - start
                MetricsCollector.record_celery_task(task_name, duration, success)
        return wrapper
    return decorator


# ============================================================
# Health Check Extensions
# ============================================================

def get_system_metrics():
    """Get current system metrics for health checks."""
    import psutil

    return {
        'cpu_percent': psutil.cpu_percent(interval=0.1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent,
        'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
    }


def check_database_health():
    """Check database connectivity and performance."""
    from django.db import connection
    import time

    start = time.time()
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        latency_ms = (time.time() - start) * 1000
        return {
            'status': 'healthy',
            'latency_ms': round(latency_ms, 2),
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
        }


def check_redis_health():
    """Check Redis connectivity."""
    from django.core.cache import cache
    import time

    start = time.time()
    try:
        cache.set('health_check', 'ok', 10)
        result = cache.get('health_check')
        latency_ms = (time.time() - start) * 1000
        if result == 'ok':
            return {
                'status': 'healthy',
                'latency_ms': round(latency_ms, 2),
            }
        return {'status': 'unhealthy', 'error': 'Cache read/write failed'}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}


def check_celery_health():
    """Check Celery worker health."""
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        active = inspect.active()
        registered = inspect.registered()

        if stats:
            worker_count = len(stats)
            return {
                'status': 'healthy',
                'workers': worker_count,
                'active_tasks': sum(len(tasks) for tasks in active.values()) if active else 0,
            }
        return {'status': 'no_workers'}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}