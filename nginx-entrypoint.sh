#!/bin/sh
# POSIX sh: the nginx:alpine image has no bash.
set -e

# Set default values for environment variables
export DOMAIN_NAME=${DOMAIN_NAME:-localhost}

# Substitute environment variables in nginx config
if [ -f /etc/nginx/nginx.conf.template ]; then
    envsubst '${DOMAIN_NAME}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
fi

# docker-compose.prod.yml replaces the image entrypoint without giving a
# command, so start nginx in the foreground unless one was passed.
if [ "$#" -eq 0 ]; then
    set -- nginx -g 'daemon off;'
fi

# Execute the main command
exec "$@"
