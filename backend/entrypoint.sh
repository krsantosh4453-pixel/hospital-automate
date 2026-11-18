#!/bin/bash
set -e

# Wait for database to be ready
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database..."
    python -c "
import os
import time
import urllib.parse
from django.db import connections
from django.db.utils import OperationalError

db_url = os.environ.get('DATABASE_URL', '')
if db_url:
    result = urllib.parse.urlparse(db_url)
    host = result.hostname
    port = result.port or 5432
    
    import socket
    start = time.time()
    while time.time() - start < 60:
        # A socket cannot be reused after a failed connect; make a new one.
        try:
            with socket.create_connection((host, port), timeout=1):
                print('Database is ready!')
                break
        except OSError:
            time.sleep(1)
    else:
        print('Database connection timeout')
        exit(1)
"
fi

# Only the web container migrates (RUN_MIGRATIONS=true); workers and beat
# share this entrypoint and must not race each other on schema changes.
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "Running migrations..."
    # Web requests keep their 30 s statement_timeout; a migration that builds
    # an index on a large table must not be killed half-way, so lift it here.
    DB_STATEMENT_TIMEOUT_MS=0 python manage.py migrate --noinput
    python manage.py load_icd10 --if-empty
    echo "Collecting static files..."
    python manage.py collectstatic --noinput

    # Optional first superuser. Only the migrating container tries, so the
    # worker and beat neither race it nor run before the tables exist.
    if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
        echo "Creating superuser..."
        python manage.py createsuperuser --noinput --username "$DJANGO_SUPERUSER_USERNAME" --email "$DJANGO_SUPERUSER_EMAIL" || echo "Superuser not created (it may already exist)."
    fi
else
    echo "RUN_MIGRATIONS is not true: skipping migrate and collectstatic in this container."
fi

# Execute the main command
exec "$@"
