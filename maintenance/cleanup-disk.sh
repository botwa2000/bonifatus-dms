#!/bin/bash
# Automated disk cleanup script for Bonifatus DMS
# Runs weekly to maintain server disk space

set -e

echo "=== Bonifatus DMS Disk Cleanup Script ==="
echo "Started at: $(date)"

# 1. Clean up Docker images older than 7 days
echo "[1/6] Cleaning old Docker images..."
docker image prune -a -f --filter "until=168h" || true

# 2. Clean up Docker build cache
echo "[2/6] Cleaning Docker build cache..."
docker builder prune -a -f --filter "until=168h" || true

# 3. Clean up unused Docker volumes
echo "[3/6] Cleaning unused Docker volumes..."
docker volume prune -f || true

# 4. Clean up stopped containers
echo "[4/6] Cleaning stopped containers..."
docker container prune -f --filter "until=168h" || true

# 5. Clean up system logs older than 7 days
echo "[5/6] Vacuuming system logs..."
journalctl --vacuum-time=7d || true

# 6. Truncate large container logs (keep last 1000 lines)
echo "[6/6] Rotating large container logs..."
for log in $(find /var/lib/docker/containers -name "*-json.log" -size +50M 2>/dev/null); do
    echo "Rotating large log: $log"
    tail -n 1000 "$log" > "$log.tmp" && mv "$log.tmp" "$log" || true
done

echo ""
echo "=== Cleanup Summary ==="
docker system df
echo ""
df -h / | grep -v Filesystem
echo ""
echo "Completed at: $(date)"
