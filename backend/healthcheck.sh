#!/bin/sh
# Smart healthcheck script that works for both backend and celery-worker services
# Detects which service is running based on CELERY_WORKER environment variable

set -e

if [ "$CELERY_WORKER" = "1" ]; then
    # Celery Worker: Check if worker is responsive
    celery -A app.celery_app inspect ping -d "celery@$(hostname)" -t 5 >/dev/null 2>&1
else
    # Backend: Check HTTP health endpoint
    curl -f http://localhost:8080/health >/dev/null 2>&1
fi
