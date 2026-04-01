#!/bin/sh
set -e

# Only run migrations/static collection if explicitly requested
# Usually only the 'web' container should do this
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "==> Running database migrations..."
    python manage.py migrate --noinput

    echo "==> Seeding initial data..."
    python manage.py seed

    echo "==> Collecting static files..."
    python manage.py collectstatic --noinput
fi

# Determine the command to run
# If no arguments, default to Gunicorn
if [ $# -eq 0 ]; then
    set -- gunicorn foodie.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers "${GUNICORN_WORKERS:-3}" \
        --timeout "${GUNICORN_TIMEOUT:-120}" \
        --access-logfile - \
        --error-logfile -
fi

echo "==> Starting: $@"

if [ -n "$NEW_RELIC_LICENSE_KEY" ]; then
    echo "==> New Relic enabled."
    export NEW_RELIC_CONFIG_FILE=newrelic.ini
    exec newrelic-admin run-program "$@"
else
    exec "$@"
fi
