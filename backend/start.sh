#!/bin/bash
# Startup script for Bonifatus DMS backend with ClamAV

set -e

echo "Starting Bonifatus DMS Backend..."

# Update ClamAV virus database (if not exists or outdated)
echo "Checking ClamAV virus database..."
if [ ! -f /var/lib/clamav/main.cvd ] && [ ! -f /var/lib/clamav/main.cld ]; then
    echo "Downloading initial ClamAV database..."
    freshclam --config-file=/etc/clamav/freshclam.conf --datadir=/var/lib/clamav || echo "Warning: Could not update ClamAV database. Will retry in background."
else
    echo "ClamAV database exists. Updating in background..."
    freshclam --daemon --config-file=/etc/clamav/freshclam.conf --datadir=/var/lib/clamav &
fi

# Start ClamAV daemon in background
echo "Starting ClamAV daemon..."
clamd --config-file=/etc/clamav/clamd.conf &

# Wait for ClamAV to be ready
echo "Waiting for ClamAV to start..."
for i in {1..30}; do
    if clamdscan --ping 2>/dev/null; then
        echo "ClamAV is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Warning: ClamAV daemon did not start in time. Continuing without active scanning..."
    fi
    sleep 1
done

# Start the Python application
echo "Starting FastAPI application..."
exec python -m app.main
