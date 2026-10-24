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
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    start = time.time()
    while time.time() - start < 60:
        try:
            sock.connect((host, port))
            sock.close()
            print('Database is ready!')
            break
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(1)
    else:
        print('Database connection timeout')
        exit(1)
"
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if needed
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser..."
    python manage.py createsuperuser --noinput --username "$DJANGO_SUPERUSER_USERNAME" --email "$DJANGO_SUPERUSER_EMAIL" || true
fi

# Execute the main command
exec "$@"
