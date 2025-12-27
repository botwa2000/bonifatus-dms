#!/bin/bash
# Startup script for Bonifatus DMS backend with lazy-loaded ClamAV
# Production-optimized for minimal memory footprint and fast startup

set -e

echo "=== Bonifatus DMS Backend - Production Startup ==="

# Environment variables for memory optimization
export MALLOC_ARENA_MAX=2  # Reduce memory fragmentation
export PYTHONMALLOC=malloc  # Use system malloc for better memory control

# Function to start ClamAV with keepalive monitoring
start_clamav_lazy() {
    echo "[ClamAV] Initializing in background (lazy mode with keepalive)..."

    # Always start in a single background process with keepalive loop
    echo "[ClamAV] Starting initialization in background..."
    (
        # Log directory created by tmpfs with root:root ownership (uid=0, gid=0)
        echo "[ClamAV] Log directory: /var/log/clamav (tmpfs mount with root:root)"

        # Update database if needed
        if [ ! -f /var/lib/clamav/main.cvd ] && [ ! -f /var/lib/clamav/main.cld ]; then
            echo "[ClamAV] No database found. Downloading..."
            freshclam --config-file=/etc/clamav/freshclam.conf --datadir=/var/lib/clamav
            if [ $? -ne 0 ]; then
                echo "[ClamAV] Database download failed. ClamAV will not be available."
                exit 1
            fi
            echo "[ClamAV] Database download complete."
        else
            echo "[ClamAV] Database exists."
        fi

        # Keepalive loop - restart clamd if it dies
        while true; do
            echo "[ClamAV] Starting daemon..."
            # Start daemon in foreground, will daemonize itself
            clamd --config-file=/etc/clamav/clamd.conf

            # Give daemon time to start
            sleep 5

            # Check if daemon is running
            if clamdscan --ping 2>/dev/null; then
                echo "[ClamAV] Daemon started successfully and is responsive"

                # Update database in background (first time only)
                if [ ! -f /var/lib/clamav/.updated ]; then
                    freshclam --config-file=/etc/clamav/freshclam.conf --datadir=/var/lib/clamav || true
                    touch /var/lib/clamav/.updated
                fi

                # Monitor loop - check every 30 seconds if daemon is still alive
                while true; do
                    sleep 30
                    if ! clamdscan --ping 2>/dev/null; then
                        echo "[ClamAV] Daemon stopped responding - restarting..."
                        pkill -9 clamd 2>/dev/null || true
                        sleep 2
                        break  # Break inner loop to restart daemon
                    fi
                done
            else
                echo "[ClamAV] Warning: Daemon failed to start, retrying in 10 seconds..."
                sleep 10
            fi
        done
    ) &

    echo "[ClamAV] Background initialization started with keepalive monitoring"
}

# Function to check if we should use lazy loading
should_lazy_load_clamav() {
    # Check if CLAMAV_LAZY_LOAD environment variable is set
    if [ "${CLAMAV_LAZY_LOAD}" = "true" ]; then
        return 0  # true - use lazy loading
    fi

    # Default: use lazy loading in production for faster startup
    if [ "${APP_ENVIRONMENT}" = "production" ]; then
        return 0  # true
    fi

    return 1  # false - load synchronously
}

# Check if ClamAV should be disabled entirely (e.g., dev environment)
if [ "${CLAMAV_ENABLED}" = "false" ]; then
    echo "[ClamAV] DISABLED - Skipping malware scanner initialization"
    echo "[ClamAV] Set CLAMAV_ENABLED=true in .env to enable"
# Determine ClamAV loading strategy
elif should_lazy_load_clamav; then
    echo "[Startup] Using LAZY LOADING strategy for ClamAV (fast startup)"
    start_clamav_lazy
else
    echo "[Startup] Using SYNCHRONOUS LOADING strategy for ClamAV"

    # Log directory created by tmpfs with root:root ownership (uid=0, gid=0)
    echo "[ClamAV] Log directory: /var/log/clamav (tmpfs mount with root:root)"

    # Update ClamAV virus database
    echo "[ClamAV] Checking virus database..."
    if [ ! -f /var/lib/clamav/main.cvd ] && [ ! -f /var/lib/clamav/main.cld ]; then
        echo "[ClamAV] Downloading initial database..."
        freshclam --config-file=/etc/clamav/freshclam.conf --datadir=/var/lib/clamav || {
            echo "[ClamAV] Warning: Database download failed. Continuing without ClamAV."
        }
    fi

    # Start ClamAV daemon (will daemonize itself)
    echo "[ClamAV] Starting daemon..."
    clamd --config-file=/etc/clamav/clamd.conf

    # Wait for ClamAV to be ready (with timeout)
    echo "[ClamAV] Waiting for daemon to start..."
    for i in {1..30}; do
        if clamdscan --ping 2>/dev/null; then
            echo "[ClamAV] Daemon is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "[ClamAV] Warning: Daemon did not start in time. Continuing anyway..."
        fi
        sleep 1
    done
fi

# Run database migrations BEFORE loading spaCy models
echo "[Database] Running migrations..."
alembic upgrade head || {
    echo "[Database] ERROR: Migrations failed"
    exit 1
}
echo "[Database] ✓ Migrations complete"

# Download spaCy models from database configuration (no hardcoded languages)
echo "[spaCy] Loading NER model configuration from database..."
python -c "
import spacy
import json
import os
from pathlib import Path
from sqlalchemy import create_engine, text

# Get database connection (from Docker secret)
def read_secret(secret_name):
    app_env = os.getenv('APP_ENVIRONMENT')
    if not app_env:
        raise RuntimeError('APP_ENVIRONMENT environment variable must be set')

    env_suffix = '_dev' if app_env == 'development' else '_prod'
    secret_path = Path(f'/run/secrets/{secret_name}{env_suffix}')

    if not secret_path.exists():
        raise ValueError(
            f'CRITICAL: Secret file {secret_path} not found. '
            f'Ensure Docker secret {secret_name}{env_suffix} is created and mounted.'
        )

    value = secret_path.read_text().strip()
    if not value:
        raise ValueError(f'CRITICAL: Secret file {secret_path} exists but is empty')

    return value

try:
    database_url = read_secret('database_url')
except (ValueError, RuntimeError) as e:
    print(f'[spaCy] ERROR: {e}')
    exit(1)

try:
    # Connect to database and load model mapping
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(
            text(\"SELECT setting_value FROM system_settings WHERE setting_key = 'spacy_model_mapping'\")
        ).fetchone()

        if not result:
            print('[spaCy] ERROR: spacy_model_mapping not found in database')
            exit(1)

        model_mapping = json.loads(result[0])
        print(f'[spaCy] Loaded model mapping from database: {model_mapping}')

    # Check which models need to be downloaded
    models_to_download = []
    for lang, model_name in model_mapping.items():
        try:
            spacy.load(model_name)
            print(f'[spaCy] ✓ {model_name} already installed')
        except OSError:
            print(f'[spaCy] {model_name} not found - will download')
            models_to_download.append((lang, model_name))

    # Download missing models
    if models_to_download:
        import subprocess
        for lang, model_name in models_to_download:
            print(f'[spaCy] Downloading {model_name}...')
            subprocess.run(['python', '-m', 'spacy', 'download', model_name], check=False)
    else:
        print('[spaCy] All required models are installed')

except Exception as e:
    print(f'[spaCy] ERROR loading models from database: {e}')
    exit(1)
" || { echo "[spaCy] FATAL: Model initialization failed"; exit 1; }

# Start the Python application (main priority)
echo "[FastAPI] Starting application on port ${APP_PORT:-8080}..."
echo "=== Application Ready ==="

exec python -m app.main
