#!/bin/bash
# Startup script for Bonifatus DMS backend with lazy-loaded ClamAV
# Production-optimized for minimal memory footprint and fast startup

set -e

echo "=== Bonifatus DMS Backend - Production Startup ==="

# Environment variables for memory optimization
export MALLOC_ARENA_MAX=2  # Reduce memory fragmentation
export PYTHONMALLOC=malloc  # Use system malloc for better memory control

# Function to start ClamAV in background (lazy loading)
start_clamav_lazy() {
    echo "[ClamAV] Initializing in background (lazy mode)..."

    # Update database in background if needed
    if [ ! -f /var/lib/clamav/main.cvd ] && [ ! -f /var/lib/clamav/main.cld ]; then
        echo "[ClamAV] No database found. Downloading in background..."
        (
            freshclam --config-file=/etc/clamav/freshclam.conf --datadir=/var/lib/clamav 2>&1 | tee -a /var/log/clamav/freshclam.log
            if [ $? -eq 0 ]; then
                echo "[ClamAV] Database download complete. Starting daemon..."
                clamd --config-file=/etc/clamav/clamd.conf 2>&1 | tee -a /var/log/clamav/clamav.log
            else
                echo "[ClamAV] Database download failed. ClamAV will not be available."
            fi
        ) &
    else
        echo "[ClamAV] Database exists. Starting daemon in background..."
        (
            # Start daemon first for faster availability
            clamd --config-file=/etc/clamav/clamd.conf 2>&1 | tee -a /var/log/clamav/clamav.log &

            # Update database in background (non-blocking)
            sleep 5  # Give daemon time to start
            freshclam --config-file=/etc/clamav/freshclam.conf --datadir=/var/lib/clamav 2>&1 | tee -a /var/log/clamav/freshclam.log || true
        ) &
    fi

    echo "[ClamAV] Background initialization started (non-blocking)"
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

# Determine ClamAV loading strategy
if should_lazy_load_clamav; then
    echo "[Startup] Using LAZY LOADING strategy for ClamAV (fast startup)"
    start_clamav_lazy
else
    echo "[Startup] Using SYNCHRONOUS LOADING strategy for ClamAV"

    # Update ClamAV virus database
    echo "[ClamAV] Checking virus database..."
    if [ ! -f /var/lib/clamav/main.cvd ] && [ ! -f /var/lib/clamav/main.cld ]; then
        echo "[ClamAV] Downloading initial database..."
        freshclam --config-file=/etc/clamav/freshclam.conf --datadir=/var/lib/clamav || {
            echo "[ClamAV] Warning: Database download failed. Continuing without ClamAV."
        }
    fi

    # Start ClamAV daemon
    echo "[ClamAV] Starting daemon..."
    clamd --config-file=/etc/clamav/clamd.conf &

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

# Start the Python application (main priority)
echo "[FastAPI] Starting application on port ${APP_PORT:-8080}..."
echo "=== Application Ready ==="

exec python -m app.main
