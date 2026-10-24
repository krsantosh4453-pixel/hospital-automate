#!/bin/bash
set -e

# Set default values for environment variables
export DOMAIN_NAME=${DOMAIN_NAME:-localhost}

# Substitute environment variables in nginx config
if [ -f /etc/nginx/nginx.conf.template ]; then
    envsubst '${DOMAIN_NAME}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
fi

# Execute the main command
exec "$@"
