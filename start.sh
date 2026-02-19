#!/usr/bin/env sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "Starting Gunicorn..."
exec gunicorn --bind :8000 --workers 2 django_project.wsgi:application