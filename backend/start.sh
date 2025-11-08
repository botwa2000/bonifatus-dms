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

    # Always start in a single background process
    echo "[ClamAV] Starting initialization in background..."
    (
        # Update database if needed
        if [ ! -f /var/lib/clamav/main.cvd ] && [ ! -f /var/lib/clamav/main.cld ]; then
            echo "[ClamAV] No database found. Downloading..."
            freshclam --config-file=/etc/clamav/freshclam.conf --datadir=/var/lib/clamav 2>&1 | tee -a /var/log/clamav/freshclam.log
            if [ $? -ne 0 ]; then
                echo "[ClamAV] Database download failed. ClamAV will not be available."
                exit 1
            fi
            echo "[ClamAV] Database download complete."
        else
            echo "[ClamAV] Database exists."
        fi

        # Create log directory if it doesn't exist
        mkdir -p /var/log/clamav
        chown clamav:clamav /var/log/clamav

        # Start daemon (always, after database is ready)
        echo "[ClamAV] Starting daemon..."
        # Start daemon in foreground, will daemonize itself
        clamd --config-file=/etc/clamav/clamd.conf

        # Give daemon time to start
        sleep 3

        # Check if daemon is running by testing the socket
        if clamdscan --ping 2>/dev/null; then
            echo "[ClamAV] Daemon started successfully and is responsive"
        else
            echo "[ClamAV] Warning: Daemon may not be fully started yet"
        fi

        # Update database in background (non-blocking)
        sleep 3
        freshclam --config-file=/etc/clamav/freshclam.conf --datadir=/var/lib/clamav 2>&1 | tee -a /var/log/clamav/freshclam.log || true
    ) &

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

    # Update ClamAV virus database
    echo "[ClamAV] Checking virus database..."
    if [ ! -f /var/lib/clamav/main.cvd ] && [ ! -f /var/lib/clamav/main.cld ]; then
        echo "[ClamAV] Downloading initial database..."
        freshclam --config-file=/etc/clamav/freshclam.conf --datadir=/var/lib/clamav || {
            echo "[ClamAV] Warning: Database download failed. Continuing without ClamAV."
        }
    fi

    # Create log directory if it doesn't exist
    mkdir -p /var/log/clamav
    chown clamav:clamav /var/log/clamav

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

# Start the Python application (main priority)
echo "[FastAPI] Starting application on port ${APP_PORT:-8080}..."
echo "=== Application Ready ==="

exec python -m app.main
