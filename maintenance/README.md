# Bonifatus DMS Server Maintenance

## Automated Cleanup Configuration

### 1. Docker Log Rotation
**File**: `/etc/docker/daemon.json`

Configured limits:
- Max log size per container: 50MB
- Max log files kept: 3 (150MB total per container)

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
```

### 2. Weekly Cleanup Script
**File**: `/usr/local/bin/cleanup-disk.sh`
**Cron**: Every Sunday at 2 AM
**Log**: `/var/log/bonifatus-cleanup.log`

The script automatically:
- Removes Docker images older than 7 days
- Cleans Docker build cache (older than 7 days)
- Removes unused Docker volumes
- Removes stopped containers (older than 7 days)
- Keeps only 7 days of system logs
- Rotates container logs larger than 50MB

### 3. Malware Protection
**Script**: `/usr/local/bin/block-malware-uid.sh`
**Timer**: Runs every 10 seconds

Removes known malware processes:
- upnpd, udhcpc, linuxsys, xmrig, cryptonight, kdevtmpfsi

### 4. Manual Cleanup Commands

Remove all unused Docker resources:
```bash
docker system prune -a -f
```

Clean specific items:
```bash
# Remove old images (7+ days)
docker image prune -a -f --filter "until=168h"

# Clean build cache
docker builder prune -a -f

# Remove unused volumes
docker volume prune -f

# Clean system logs
journalctl --vacuum-time=7d
```

## Performance Baseline

After optimization (2026-01-07):
- Disk usage: 33% (24GB/75GB) - freed 17GB
- Memory: 4.5GB/7.7GB used (58%)
- API response time: ~0.5s
- Frontend load time: ~1-2s

## Monitoring Commands

Check disk space:
```bash
df -h /
docker system df
```

Check memory:
```bash
free -h
docker stats --no-stream
```

Check logs size:
```bash
journalctl --disk-usage
find /var/lib/docker/containers -name "*-json.log" -exec du -sh {} \; | sort -rh | head -10
```

Check I/O performance:
```bash
iostat -x 2 3
```

## Maintenance Schedule

- **Daily**: Malware blocker runs every 10 seconds
- **Weekly**: Disk cleanup runs Sunday 2 AM
- **Monthly**: Review logs and adjust cleanup policies if needed
- **Quarterly**: Review disk usage trends and adjust retention

## Emergency Cleanup

If disk reaches 80%:
```bash
# Run cleanup immediately
/usr/local/bin/cleanup-disk.sh

# Check for large files
du -sh /var/lib/docker/* | sort -rh | head -10

# Remove specific stopped containers
docker ps -a --filter "status=exited" -q | xargs docker rm

# Remove all dangling images
docker images -f "dangling=true" -q | xargs docker rmi
```
