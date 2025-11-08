# Server Stabilization & Configuration Steps

**Current Status:** Server is overloaded with both prod and dev ClamAV instances starting simultaneously (4GB RAM server).

## What's Been Deployed

✅ **Production:**
- ClamAV fix deployed and running (file uploads should work now)
- Tier system code deployed (migration not run yet)

✅ **Development:**
- Code pulled but container is overloaded
- ClamAV disable feature added (not applied yet)

## Manual Steps to Complete (Run after 10-15 minutes)

### Step 1: Verify Server Stability

```bash
ssh root@91.99.212.17

# Check memory usage
free -h

# Check container status
docker ps

# Should show both backend containers running and healthy
```

### Step 2: Configure Dev Environment

#### 2A: Disable ClamAV on Dev (Saves 1.3GB RAM)

```bash
# Add to dev .env
echo 'CLAMAV_ENABLED=false' >> /opt/bonifatus-dms-dev/.env

# Verify it was added
grep CLAMAV /opt/bonifatus-dms-dev/.env

# Restart dev backend to apply
cd /opt/bonifatus-dms-dev
docker compose restart backend

# Wait 30 seconds, then check logs
docker logs bonifatus-backend-dev --tail 20
# Should see: [ClamAV] DISABLED - Skipping malware scanner initialization
```

#### 2B: Run Tier Migration on Dev

```bash
# Run migration
docker exec bonifatus-backend-dev alembic upgrade head

# Verify tier tables were created
PGPASSWORD=BoniDocDev2025Password psql -h localhost -U bonifatus_dev -d bonifatus_dms_dev -c "SELECT id, name, display_name, price_monthly_cents FROM tier_plans ORDER BY id;"

# Expected output:
#  id  |  name   | display_name  | price_monthly_cents
# -----+---------+---------------+--------------------
#   0  | free    | Free          |                 0
#   1  | starter | Starter       |               999
#   2  | pro     | Professional  |              2999
# 100  | admin   | Administrator |                 0
```

### Step 3: Configure IP Whitelist for Dev

**First, find your IP:**
```bash
curl https://api.ipify.org
# Example output: 203.0.113.45
```

**Then apply whitelist:**
```bash
ssh root@91.99.212.17

# Download the template config
cd /opt/bonifatus-dms
git pull origin main

# Copy template to nginx
cp nginx-dev-ip-whitelist.conf /etc/nginx/sites-available/dev.bonidoc.com

# Edit and replace YOUR_IP_ADDRESS with actual IP
nano /etc/nginx/sites-available/dev.bonidoc.com
# Find line: YOUR_IP_ADDRESS 1;
# Replace with: 203.0.113.45 1;  (use your actual IP)

# Test nginx config
nginx -t

# If OK, reload
systemctl reload nginx

# Test access from browser
# Should work: https://dev.bonidoc.com (from your IP)
# Should fail: https://dev.bonidoc.com (from different IP/VPN)
```

See `CONFIGURE_DEV_IP_WHITELIST.md` for detailed instructions.

### Step 4: Test Production File Upload

```bash
# Test that ClamAV is working on production
curl https://api.bonidoc.com/health

# Should show:
# "malware_scanner": {
#   "clamav": "available",
#   "clamav_version": "ClamAV 1.4.3/27816/..."
# }
```

Then test file upload via the UI at https://bonidoc.com - should work without "Connection refused" errors.

### Step 5: Run Tier Migration on Production (LATER)

**⚠️ DO NOT RUN YET** - Test on dev first!

Once dev tier system is tested and working:

```bash
ssh root@91.99.212.17

# Backup production database first
pg_dump -U bonifatus -d bonifatus_dms > /tmp/backup_before_tier_$(date +%Y%m%d).sql

# Run migration
cd /opt/bonifatus-dms
docker exec bonifatus-backend alembic upgrade head

# Verify
PGPASSWORD=BoniDoc2025SecurePassword psql -h localhost -U bonifatus -d bonifatus_dms -c "SELECT id, name, display_name FROM tier_plans ORDER BY id;"

# Check backend health
curl https://api.bonidoc.com/health
```

## Current Resource Usage

**Before changes:**
- Prod backend: ~1.3GB (ClamAV running)
- Dev backend: ~1.3GB (ClamAV running)
- Total: ~2.6GB on 4GB server = **65% memory usage**

**After disabling ClamAV on dev:**
- Prod backend: ~1.3GB (ClamAV running - needed)
- Dev backend: ~300MB (ClamAV disabled)
- Total: ~1.6GB on 4GB server = **40% memory usage**

## Troubleshooting

### Server Still Slow/Timing Out

```bash
# Check memory
free -h

# Check processes
top -bn1 | head -20

# If ClamAV is consuming too much memory, you can:
# 1. Wait for database download to complete (~10-15 min)
# 2. Or restart containers to free memory
docker compose -f /opt/bonifatus-dms/docker-compose.yml restart
docker compose -f /opt/bonifatus-dms-dev/docker-compose.yml restart
```

### Can't Access Dev After IP Whitelist

1. Verify your IP: `curl https://api.ipify.org`
2. Check nginx config has correct IP
3. Check nginx error log: `tail -f /var/log/nginx/error.log`
4. Temporarily disable whitelist to test:
   ```bash
   # Comment out the IP check in nginx config
   nano /etc/nginx/sites-available/dev.bonidoc.com
   # Comment out: if ($dev_allowed = 0) { return 403; }
   nginx -t && systemctl reload nginx
   ```

### Migration Fails

```bash
# Check alembic version
docker exec bonifatus-backend-dev alembic current

# Check migration history
docker exec bonifatus-backend-dev alembic history

# If stuck, check database connection
docker exec bonifatus-backend-dev alembic show head
```

## Next Steps After Stabilization

1. ✅ Dev environment accessible only from your IP
2. ✅ ClamAV disabled on dev (saves RAM)
3. ✅ Tier system migrated to dev database
4. ⏳ Test tier system on dev
5. ⏳ Deploy tier system to production
6. ⏳ Build admin dashboard for tier management
7. ⏳ Integrate frontend with tier limits

## Contact/Support

If you encounter issues:
1. Check server logs: `journalctl -xe`
2. Check container logs: `docker logs <container_name>`
3. Check nginx logs: `/var/log/nginx/error.log`
4. Verify network connectivity: `ping 91.99.212.17`

---

**Created:** 2025-11-08
**Status:** Pending server stabilization
**Estimated Time:** 10-15 minutes for ClamAV to finish initializing
