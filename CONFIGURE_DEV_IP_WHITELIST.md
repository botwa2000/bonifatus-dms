# Configure IP Whitelist for Development Environment

This guide explains how to restrict access to dev.bonidoc.com to only your IP address.

## Why IP Whitelist?

Development environment should not be publicly accessible:
- Prevents unauthorized access to test data
- Protects work-in-progress features
- Reduces attack surface
- Saves resources (no random traffic)

## Step 1: Find Your IP Address

**Option A:** Visit https://whatismyipaddress.com/

**Option B:** Run this command:
```bash
curl https://api.ipify.org
```

**Example output:** `203.0.113.45`

## Step 2: Update Nginx Configuration on Server

```bash
# SSH to server
ssh root@91.99.212.17

# Edit the nginx config
nano /etc/nginx/sites-available/dev.bonidoc.com

# Find the line with YOUR_IP_ADDRESS and replace it with your actual IP
# For example, if your IP is 203.0.113.45:
# Change: YOUR_IP_ADDRESS 1;
# To:     203.0.113.45 1;

# For IP ranges (e.g., office network):
# 198.51.100.0/24 1;

# To add multiple IPs:
geo $dev_allowed {
    default 0;
    203.0.113.45 1;     # Home
    198.51.100.50 1;    # Office
    10.0.0.0/8 1;       # VPN network
}
```

## Step 3: Apply Configuration

```bash
# Test nginx configuration
nginx -t

# If test passes, reload nginx
systemctl reload nginx

# Check nginx status
systemctl status nginx
```

## Step 4: Test Access

**From allowed IP (should work):**
```bash
curl -I https://dev.bonidoc.com
# Expected: HTTP/2 200
```

**From different IP or incognito/VPN:**
```bash
curl -I https://dev.bonidoc.com
# Expected: HTTP/2 403 Forbidden
```

## Troubleshooting

### Can't Access Dev Environment

1. **Verify your current IP:**
   ```bash
   curl https://api.ipify.org
   ```

2. **Check nginx config:**
   ```bash
   ssh root@91.99.212.17
   grep -A 10 'geo $dev_allowed' /etc/nginx/sites-available/dev.bonidoc.com
   ```

3. **Check nginx error log:**
   ```bash
   tail -f /var/log/nginx/error.log
   ```

### IP Changed (Dynamic IP)

If your ISP gives you a dynamic IP that changes:

**Option A:** Add IP range instead of single IP:
```nginx
203.0.113.0/24 1;  # Allows entire /24 block
```

**Option B:** Use VPN with static IP

**Option C:** Update nginx config when IP changes:
```bash
ssh root@91.99.212.17
nano /etc/nginx/sites-available/dev.bonidoc.com
# Update IP
nginx -t && systemctl reload nginx
```

## Alternative: Environment Variable Approach

For more flexibility, you can store allowed IPs in the dev .env file:

1. **Add to `/opt/bonifatus-dms-dev/.env`:**
   ```bash
   DEV_ALLOWED_IPS="203.0.113.45,198.51.100.50"
   ```

2. **Create nginx config template** that reads from environment

3. **Regenerate config on deployment**

This approach is more complex but allows IP management without editing nginx configs directly.

## Security Notes

- **Do NOT** whitelist `0.0.0.0/0` (allows everyone)
- **Do NOT** use production IP whitelist (prod should be public)
- **Keep** your IP list minimal (only trusted IPs)
- **Update** the list when team members join/leave
- **Consider** using VPN for remote team access instead of whitelisting many IPs

## Cloudflare Considerations

Since you're using Cloudflare proxy:
- Cloudflare IPs will be in `X-Forwarded-For` header
- The `$remote_addr` in nginx will be Cloudflare's IP
- Use `set_real_ip_from` directive to get actual client IP

**Add to nginx http block:**
```nginx
# Cloudflare IP ranges
set_real_ip_from 173.245.48.0/20;
set_real_ip_from 103.21.244.0/22;
set_real_ip_from 103.22.200.0/22;
set_real_ip_from 103.31.4.0/22;
set_real_ip_from 141.101.64.0/18;
set_real_ip_from 108.162.192.0/18;
set_real_ip_from 190.93.240.0/20;
set_real_ip_from 188.114.96.0/20;
set_real_ip_from 197.234.240.0/22;
set_real_ip_from 198.41.128.0/17;
set_real_ip_from 162.158.0.0/15;
set_real_ip_from 104.16.0.0/13;
set_real_ip_from 104.24.0.0/14;
set_real_ip_from 172.64.0.0/13;
set_real_ip_from 131.0.72.0/22;
real_ip_header X-Forwarded-For;
real_ip_recursive on;
```

This ensures IP whitelist works correctly with Cloudflare proxy.
