# Hetzner Migration Guide - Complete Setup from Scratch

**Date:** October 23, 2025
**From:** Google Cloud Run
**To:** Hetzner VPS
**Estimated Time:** 2-3 hours
**Cost:** ~€5/month vs ~$25-50/month on Cloud Run

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Server Selection & Setup](#server-selection--setup)
3. [Initial Server Configuration](#initial-server-configuration)
4. [Install Required Software](#install-required-software)
5. [PostgreSQL Setup](#postgresql-setup)
6. [Application Deployment](#application-deployment)
7. [SSL Certificate Setup](#ssl-certificate-setup)
8. [DNS Configuration](#dns-configuration)
9. [GitHub Integration](#github-integration)
10. [Google Services Configuration](#google-services-configuration)
11. [Environment Variables](#environment-variables)
12. [Logging & Monitoring](#logging--monitoring)
13. [VS Code Remote Development](#vs-code-remote-development)
14. [Backup Strategy](#backup-strategy)
15. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### What You'll Need
- [ ] Hetzner account (create at https://hetzner.com)
- [ ] Credit card or PayPal for Hetzner payment
- [ ] Domain name (bonidoc.com) - you already have this
- [ ] SSH client (Windows: Git Bash, PowerShell, or PuTTY)
- [ ] VS Code installed on your local machine
- [ ] Your Google Cloud credentials (for Drive, Vision OCR, OAuth)

### Existing Credentials to Have Ready
- [ ] Database credentials (Supabase connection string)
- [ ] Google OAuth Client ID & Secret
- [ ] Google Drive Service Account Key
- [ ] Security secret keys
- [ ] Encryption keys

---

## 1. Server Selection & Setup

### 1.1 Create Hetzner Account

1. Go to https://www.hetzner.com/cloud
2. Click **"Sign Up"**
3. Fill in your details:
   - Email address
   - Password
   - Accept terms
4. Verify your email
5. Add payment method (credit card or PayPal)

### 1.2 Create a New Project

1. Log in to Hetzner Cloud Console: https://console.hetzner.cloud
2. Click **"New Project"**
3. Name it: `bonifatus-dms`
4. Click **"Create Project"**

### 1.3 Create Your Server (VPS)

1. Inside your project, click **"Add Server"**

2. **Location:** Choose closest to your users
   - Recommended: `Ashburn, VA` (if US-based)
   - Or: `Nuremberg, Germany` (EU)

3. **Image:**
   - Select **"Ubuntu 24.04"** (latest LTS)

4. **Type:**
   - **Recommended:** `CPX21` (3 vCPU, 4GB RAM, 80GB SSD) - €8.21/month
   - **Budget:** `CPX11` (2 vCPU, 2GB RAM, 40GB SSD) - €4.75/month
   - **Note:** For ClamAV malware scanner, minimum 2GB RAM is needed

5. **Networking:**
   - ✅ Enable **IPv4**
   - ✅ Enable **IPv6**

6. **SSH Keys:**
   - Click **"Add SSH key"**
   - **On Windows (Git Bash or PowerShell):**
     ```bash
     # Check if you already have an SSH key
     ls ~/.ssh/id_rsa.pub

     # If not, generate one
     ssh-keygen -t rsa -b 4096 -C "your-email@example.com"
     # Press Enter for all prompts (default location, no passphrase for simplicity)

     # Display your public key
     cat ~/.ssh/id_rsa.pub
     ```
   - Copy the entire output (starts with `ssh-rsa`)
   - Paste it into Hetzner's SSH key field
   - Name it: `my-laptop`

7. **Firewalls:**
   - Click **"Create Firewall"**
   - Name: `bonifatus-firewall`
   - **Inbound Rules:**
     ```
     SSH      TCP    22      0.0.0.0/0, ::/0
     HTTP     TCP    80      0.0.0.0/0, ::/0
     HTTPS    TCP    443     0.0.0.0/0, ::/0
     ```
   - **Outbound Rules:**
     ```
     All      All    All     0.0.0.0/0, ::/0
     ```
   - Click **"Create Firewall"**
   - Select this firewall for your server

8. **Additional Features:**
   - ✅ Enable **Backups** (+20% cost, highly recommended)

9. **Server Name:** `bonifatus-prod`

10. Click **"Create & Buy Now"**

11. **Wait 1-2 minutes** for server creation

12. **Copy Your Server IP Address**
    - You'll see it in the server details
    - Example: `65.108.123.456`
    - Save this somewhere - you'll need it!

---

## 2. Initial Server Configuration

### 2.1 First Login

1. Open your terminal (Git Bash, PowerShell, or Terminal)

2. Connect to your server:
   ```bash
   ssh root@YOUR_SERVER_IP
   # Replace YOUR_SERVER_IP with the actual IP from Hetzner
   # Example: ssh root@65.108.123.456
   ```

3. Type `yes` when asked about fingerprint

4. You should see a welcome message and Ubuntu prompt:
   ```
   root@bonifatus-prod:~#
   ```

### 2.2 Update System

```bash
# Update package list
apt update

# Upgrade all packages (this may take 5-10 minutes)
apt upgrade -y

# Install essential tools
apt install -y curl wget git vim nano htop unzip build-essential
```

### 2.3 Create Non-Root User (Security Best Practice)

```bash
# Create a new user
adduser deploy
# Enter password when prompted (save this password!)
# Press Enter for all other prompts (use defaults)

# Add user to sudo group
usermod -aG sudo deploy

# Add your SSH key to the new user
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
```

### 2.4 Test New User Login

1. **Keep your root session open** (don't close it yet)
2. Open a **new terminal window**
3. Test login:
   ```bash
   ssh deploy@YOUR_SERVER_IP
   ```
4. If it works, you're good! Keep both terminals open for now.

### 2.5 Secure SSH (Optional but Recommended)

```bash
# Switch to deploy user if not already
sudo nano /etc/ssh/sshd_config

# Find and change these lines (use Ctrl+W to search):
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes

# Save and exit (Ctrl+X, then Y, then Enter)

# Restart SSH service
sudo systemctl restart sshd
```

**⚠️ WARNING:** Only do this AFTER confirming you can login as `deploy` user!

---

## 3. Install Required Software

From now on, work as the `deploy` user. If you're still logged in as root, switch:

```bash
su - deploy
# Or logout and login as deploy
```

### 3.1 Install Docker & Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group (avoid sudo for docker commands)
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes to take effect
exit
# Then reconnect: ssh deploy@YOUR_SERVER_IP

# Verify installation
docker --version
docker-compose --version
```

### 3.2 Install Node.js (for frontend builds)

```bash
# Install Node.js 20.x LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installation
node --version
npm --version
```

### 3.3 Install Nginx (Reverse Proxy)

```bash
sudo apt install -y nginx

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Check status
sudo systemctl status nginx
# Press 'q' to exit status view
```

### 3.4 Install Certbot (for SSL certificates)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Verify installation
certbot --version
```

---

## 4. PostgreSQL Setup

You have two options:

### Option A: Keep Using Supabase (Recommended - Easiest)

✅ **Keep your existing Supabase database** - no migration needed!

Just use your existing `DATABASE_URL` from Cloud Run. Skip to section 5.

### Option B: Install PostgreSQL on Hetzner (Full Control)

```bash
# Install PostgreSQL 16
sudo apt install -y postgresql-16 postgresql-contrib-16

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Switch to postgres user
sudo -i -u postgres

# Create database and user
psql
```

Inside PostgreSQL prompt:
```sql
-- Create user
CREATE USER bonifatus WITH PASSWORD 'your-strong-password-here';

-- Create database
CREATE DATABASE bonifatus_dms OWNER bonifatus;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE bonifatus_dms TO bonifatus;

-- Enable required extensions
\c bonifatus_dms
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Exit
\q
```

Exit postgres user:
```bash
exit
```

Configure PostgreSQL for remote access (if needed):
```bash
sudo nano /etc/postgresql/16/main/postgresql.conf

# Find and change:
listen_addresses = 'localhost'  # Keep as localhost for security

# Save and exit

sudo nano /etc/postgresql/16/main/pg_hba.conf

# Add this line at the end:
local   all             bonifatus                               scram-sha-256

# Save and exit

# Restart PostgreSQL
sudo systemctl restart postgresql
```

Your database connection string:
```
DATABASE_URL=postgresql://bonifatus:your-strong-password-here@localhost:5432/bonifatus_dms
```

**For this guide, we'll assume you're using Option A (Supabase).**

---

## 5. Application Deployment

### 5.1 Create Application Directory

```bash
# Create directory structure
sudo mkdir -p /opt/bonifatus-dms
sudo chown -R deploy:deploy /opt/bonifatus-dms
cd /opt/bonifatus-dms
```

### 5.2 Clone Your Repository

```bash
# Clone from GitHub
git clone https://github.com/botwa2000/bonifatus-dms.git .

# Verify files
ls -la
# You should see: backend/, frontend/, .github/, etc.
```

### 5.3 Create Environment File

```bash
# Create .env file
nano .env
```

Paste this content (fill in your actual values):

```env
# === Application Settings ===
APP_ENVIRONMENT=production
APP_DEBUG_MODE=false
APP_CORS_ORIGINS=https://bonidoc.com,https://www.bonidoc.com
APP_HOST=0.0.0.0
APP_PORT=8080
APP_TITLE=Bonifatus DMS
APP_DESCRIPTION=Professional Document Management System
APP_VERSION=1.0.0
HOST=0.0.0.0

# === Database Settings (Supabase) ===
DATABASE_URL=postgresql://postgres.xxxxx:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
DATABASE_POOL_SIZE=10
DATABASE_POOL_RECYCLE=60
DATABASE_ECHO=false
DATABASE_POOL_PRE_PING=true
DATABASE_CONNECT_TIMEOUT=60

# === Google OAuth Settings ===
GOOGLE_CLIENT_ID=356302004293-xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
GOOGLE_REDIRECT_URI=https://bonidoc.com/login
GOOGLE_VISION_ENABLED=true
GOOGLE_OAUTH_ISSUERS=https://accounts.google.com

# === Google Drive Settings ===
GOOGLE_DRIVE_FOLDER_NAME=Bonifatus_DMS
GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY=/app/secrets/google-drive-key.json
GCP_PROJECT=bon-dms

# === Security Settings ===
SECURITY_SECRET_KEY=your-secret-key-here-min-32-chars
ENCRYPTION_KEY=your-encryption-key-here-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
DEFAULT_USER_TIER=free
ADMIN_EMAILS=bonifatus.app@gmail.com

# === Frontend Settings ===
NEXT_PUBLIC_API_URL=https://api.bonidoc.com
```

Save and exit (Ctrl+X, Y, Enter)

### 5.4 Create Secrets Directory

```bash
# Create secrets directory
mkdir -p secrets

# Create Google Drive service account key file
nano secrets/google-drive-key.json
```

Paste your Google Drive service account JSON key (the entire JSON content), then save.

```bash
# Secure the secrets
chmod 600 secrets/google-drive-key.json
chmod 700 secrets
```

### 5.5 Create Docker Compose File

```bash
nano docker-compose.yml
```

Paste this content:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: bonifatus-backend
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - APP_ENVIRONMENT=${APP_ENVIRONMENT}
      - APP_DEBUG_MODE=${APP_DEBUG_MODE}
      - APP_CORS_ORIGINS=${APP_CORS_ORIGINS}
      - APP_HOST=${APP_HOST}
      - APP_PORT=${APP_PORT}
      - APP_TITLE=${APP_TITLE}
      - APP_DESCRIPTION=${APP_DESCRIPTION}
      - APP_VERSION=${APP_VERSION}
      - DATABASE_URL=${DATABASE_URL}
      - DATABASE_POOL_SIZE=${DATABASE_POOL_SIZE}
      - DATABASE_POOL_RECYCLE=${DATABASE_POOL_RECYCLE}
      - DATABASE_ECHO=${DATABASE_ECHO}
      - DATABASE_POOL_PRE_PING=${DATABASE_POOL_PRE_PING}
      - DATABASE_CONNECT_TIMEOUT=${DATABASE_CONNECT_TIMEOUT}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - GOOGLE_REDIRECT_URI=${GOOGLE_REDIRECT_URI}
      - GOOGLE_VISION_ENABLED=${GOOGLE_VISION_ENABLED}
      - GOOGLE_OAUTH_ISSUERS=${GOOGLE_OAUTH_ISSUERS}
      - GOOGLE_DRIVE_FOLDER_NAME=${GOOGLE_DRIVE_FOLDER_NAME}
      - GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY=${GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY}
      - GCP_PROJECT=${GCP_PROJECT}
      - SECURITY_SECRET_KEY=${SECURITY_SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - ALGORITHM=${ALGORITHM}
      - ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES}
      - REFRESH_TOKEN_EXPIRE_DAYS=${REFRESH_TOKEN_EXPIRE_DAYS}
      - DEFAULT_USER_TIER=${DEFAULT_USER_TIER}
      - ADMIN_EMAILS=${ADMIN_EMAILS}
    volumes:
      - ./secrets:/app/secrets:ro
      - backend-data:/var/lib/clamav
    networks:
      - bonifatus-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
    container_name: bonifatus-frontend
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
    networks:
      - bonifatus-network
    depends_on:
      backend:
        condition: service_healthy

volumes:
  backend-data:

networks:
  bonifatus-network:
    driver: bridge
```

Save and exit.

### 5.6 Build and Start Application

```bash
# Build images (this will take 10-15 minutes first time)
docker-compose build

# Start containers
docker-compose up -d

# Check if containers are running
docker-compose ps

# View logs
docker-compose logs -f
# Press Ctrl+C to stop viewing logs
```

### 5.7 Verify Application is Running

```bash
# Test backend health
curl http://localhost:8080/health

# You should see JSON response with "status": "healthy"

# Test frontend
curl http://localhost:3000

# You should see HTML content
```

---

## 6. SSL Certificate Setup

**Note:** This guide provides two options for SSL setup:
- **Option A**: Cloudflare Origin Certificate (Recommended - Used in production)
- **Option B**: Let's Encrypt with Certbot (Alternative)

### Option A: Cloudflare Origin Certificate (RECOMMENDED - PRODUCTION METHOD)

This is the method used in the actual production deployment. Cloudflare handles public SSL/TLS, and an origin certificate secures traffic between Cloudflare and your server.

**Benefits:**
- Free unlimited SSL certificates
- DDoS protection
- CDN caching
- Automatic renewals
- No need to open port 80 for verification

**Setup Steps:**

1. **Get Cloudflare Origin Certificate**
   - Log in to Cloudflare dashboard
   - Select your domain (bonidoc.com)
   - Go to SSL/TLS → Origin Server
   - Click "Create Certificate"
   - Leave defaults (15 year validity, RSA 2048, all hostnames)
   - Click "Create"
   - Copy the certificate and private key

2. **Install Certificate on Server**
   ```bash
   # Create SSL directory
   sudo mkdir -p /etc/ssl/cloudflare

   # Create certificate file
   sudo nano /etc/ssl/cloudflare/bonidoc.com.pem
   # Paste the origin certificate, save and exit

   # Create private key file
   sudo nano /etc/ssl/cloudflare/bonidoc.com.key
   # Paste the private key, save and exit

   # Secure the files
   sudo chmod 644 /etc/ssl/cloudflare/bonidoc.com.pem
   sudo chmod 600 /etc/ssl/cloudflare/bonidoc.com.key
   sudo chown root:root /etc/ssl/cloudflare/bonidoc.com.*
   ```

3. **Configure Cloudflare SSL Mode**
   - In Cloudflare dashboard: SSL/TLS → Overview
   - Set encryption mode to **"Full (strict)"**
   - This ensures end-to-end encryption

4. **Configure DNS** (must be done before Nginx)
   - In Cloudflare dashboard: DNS → Records
   - Add A records with proxy enabled (orange cloud):
     - `@` → Your server IP (91.99.212.17)
     - `www` → Your server IP
     - `api` → Your server IP

5. **Configure Nginx with Cloudflare Certificate**

See section 6.1 below for Nginx configuration (use Cloudflare certificate paths).

### Option B: Let's Encrypt with Certbot (ALTERNATIVE)

If you prefer Let's Encrypt certificates instead of Cloudflare:
- Follow the original guide in sections 6.1-6.4 below
- Use Let's Encrypt certificate paths in Nginx config
- Disable Cloudflare proxy (gray cloud) in DNS settings

---

### 6.1 Configure Nginx as Reverse Proxy

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/bonidoc.com
```

Paste this content:

```nginx
# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name bonidoc.com www.bonidoc.com;

    # Let's Encrypt verification
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS - Main website (frontend)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name bonidoc.com www.bonidoc.com;

    # SSL certificates (will be configured by certbot)
    ssl_certificate /etc/letsencrypt/live/bonidoc.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bonidoc.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy to frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}

# HTTPS - API subdomain (backend)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.bonidoc.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/bonidoc.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bonidoc.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy to backend
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS headers (backend also sets these, but Nginx adds as backup)
        add_header Access-Control-Allow-Origin "https://bonidoc.com" always;
        add_header Access-Control-Allow-Credentials "true" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
        add_header Access-Control-Allow-Headers "*" always;

        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin "https://bonidoc.com" always;
            add_header Access-Control-Allow-Credentials "true" always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
            add_header Access-Control-Allow-Headers "*" always;
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
    }
}
```

Save and exit.

### 6.2 Enable Site Configuration

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/bonidoc.com /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# If test passes, reload Nginx
sudo systemctl reload nginx
```

### 6.3 Obtain SSL Certificate

**BEFORE running this, make sure your DNS is already pointing to this server!** (See section 7)

```bash
# Obtain certificate for all domains
sudo certbot --nginx -d bonidoc.com -d www.bonidoc.com -d api.bonidoc.com

# Follow the prompts:
# - Enter your email address
# - Agree to terms (Y)
# - Share email with EFF (optional, N is fine)
# - Certbot will automatically configure Nginx

# Test automatic renewal
sudo certbot renew --dry-run
```

### 6.4 Set Up Auto-Renewal

```bash
# Certbot automatically sets up renewal, verify it:
sudo systemctl status certbot.timer

# Should show "active (waiting)"
```

---

## 7. DNS Configuration

You need to update your domain DNS records to point to your Hetzner server.

### 7.1 Get Your Server IP

```bash
# Already noted earlier, but if you forgot:
curl ifconfig.me
```

### 7.2 Update DNS Records

Go to your domain registrar (where you bought bonidoc.com):

**Delete or disable ALL existing DNS records for bonidoc.com**

**Add these A records:**

| Type | Name | Value (IP Address) | TTL |
|------|------|-------------------|-----|
| A | @ | YOUR_SERVER_IP | 3600 |
| A | www | YOUR_SERVER_IP | 3600 |
| A | api | YOUR_SERVER_IP | 3600 |

**Example (if your server IP is 65.108.123.456):**
```
A    @      65.108.123.456    3600
A    www    65.108.123.456    3600
A    api    65.108.123.456    3600
```

### 7.3 Wait for DNS Propagation

DNS changes can take 5 minutes to 24 hours to propagate globally. Usually 5-30 minutes.

**Check propagation:**
```bash
# From your local computer
nslookup bonidoc.com
nslookup api.bonidoc.com

# You should see your server IP in the result
```

### 7.4 Test After DNS Propagates

```bash
# From your local computer
curl http://bonidoc.com
curl http://api.bonidoc.com/health

# Both should work
```

**Now go back to section 6.3 and run certbot if you haven't yet!**

---

## 8. GitHub Integration

### 8.1 Set Up Deploy Key

```bash
# On your server, generate a deploy key
ssh-keygen -t ed25519 -C "deploy@bonifatus-dms" -f ~/.ssh/deploy_key

# Display the public key
cat ~/.ssh/deploy_key.pub
```

Copy the entire output.

### 8.2 Add Deploy Key to GitHub

1. Go to: https://github.com/botwa2000/bonifatus-dms/settings/keys
2. Click **"Add deploy key"**
3. Title: `Hetzner Production Server`
4. Paste the public key
5. ✅ Check **"Allow write access"** (if you want to push from server)
6. Click **"Add key"**

### 8.3 Configure Git on Server

```bash
# Tell git to use the deploy key
cat >> ~/.ssh/config << 'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/deploy_key
    IdentitiesOnly yes
EOF

chmod 600 ~/.ssh/config

# Test connection
ssh -T git@github.com
# You should see: "Hi botwa2000! You've successfully authenticated..."
```

### 8.4 Set Up Git in Application Directory

```bash
cd /opt/bonifatus-dms

# Set git user (for commits if needed)
git config user.name "Bonifatus Server"
git config user.email "deploy@bonidoc.com"

# Verify remote
git remote -v
```

### 8.5 Create Deployment Script

```bash
nano ~/deploy.sh
```

Paste this content:

```bash
#!/bin/bash
set -e

echo "🚀 Starting deployment..."

cd /opt/bonifatus-dms

# Pull latest code
echo "📦 Pulling latest code from GitHub..."
git pull origin main

# Rebuild and restart containers
echo "🔨 Rebuilding containers..."
docker-compose build

echo "🔄 Restarting services..."
docker-compose down
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed"
    docker-compose logs backend
    exit 1
fi

if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is healthy"
else
    echo "❌ Frontend health check failed"
    docker-compose logs frontend
    exit 1
fi

echo "✅ Deployment completed successfully!"
echo "🌐 Frontend: https://bonidoc.com"
echo "🔧 API: https://api.bonidoc.com"
```

Save and exit, then:

```bash
chmod +x ~/deploy.sh
```

### 8.6 Test Deployment Script

```bash
~/deploy.sh
```

---

## 9. Google Services Configuration

### 9.1 Update Google OAuth Redirect URI

1. Go to: https://console.cloud.google.com/apis/credentials
2. Select your project: `bon-dms`
3. Click on your OAuth 2.0 Client ID
4. Under **"Authorized redirect URIs"**, add:
   ```
   https://bonidoc.com/login
   ```
5. Remove the old Cloud Run URLs
6. Click **"Save"**

### 9.2 Update Google Drive Service Account

Already done! The service account key is in `/opt/bonifatus-dms/secrets/google-drive-key.json`

### 9.3 Test Google Services

```bash
# Test OAuth (from your browser)
# Visit: https://bonidoc.com
# Try to login with Google

# Test Drive API (from server)
docker-compose logs backend | grep -i "drive"
# Should see: "Drive credentials created successfully"

# Test Vision OCR (upload a document after deployment)
```

---

## 10. Environment Variables

### 10.1 Environment File Location

Main environment file: `/opt/bonifatus-dms/.env`

### 10.2 Update Environment Variables

```bash
cd /opt/bonifatus-dms
nano .env

# Edit values as needed
# Save and exit

# Restart services to apply changes
docker-compose down
docker-compose up -d
```

### 10.3 Environment Variables Checklist

Make sure these are all set correctly in `.env`:

- [ ] `DATABASE_URL` - Your Supabase connection string
- [ ] `GOOGLE_CLIENT_ID` - From Google Cloud Console
- [ ] `GOOGLE_CLIENT_SECRET` - From Google Cloud Console
- [ ] `GOOGLE_REDIRECT_URI` - `https://bonidoc.com/login`
- [ ] `SECURITY_SECRET_KEY` - Random 32+ character string
- [ ] `ENCRYPTION_KEY` - Random 32 character string
- [ ] `ADMIN_EMAILS` - Your admin email
- [ ] `NEXT_PUBLIC_API_URL` - `https://api.bonidoc.com`

### 10.4 Generate Secret Keys (if needed)

```bash
# Generate secure random keys
openssl rand -base64 32
# Use output for SECURITY_SECRET_KEY or ENCRYPTION_KEY
```

---

## 11. Logging & Monitoring

### 11.1 View Application Logs

```bash
# View all logs
docker-compose logs -f

# View backend logs only
docker-compose logs -f backend

# View frontend logs only
docker-compose logs -f frontend

# View last 100 lines
docker-compose logs --tail=100

# Search logs
docker-compose logs | grep "ERROR"
```

### 11.2 Set Up Log Rotation

```bash
# Create log rotation config
sudo nano /etc/docker/daemon.json
```

Paste this:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Save and exit, then:

```bash
sudo systemctl restart docker
docker-compose down
docker-compose up -d
```

### 11.3 System Monitoring

```bash
# Install monitoring tools
sudo apt install -y htop iotop

# Monitor resource usage
htop
# Press 'q' to quit

# Monitor disk usage
df -h

# Monitor Docker stats
docker stats
```

### 11.4 Set Up Simple Log Viewer (Optional)

```bash
# Install dozzle - web-based log viewer
docker run -d --name dozzle -p 9999:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  amir20/dozzle:latest
```

Access logs at: `http://YOUR_SERVER_IP:9999`

**Security Note:** Only access this from your home IP or set up authentication!

---

## 12. VS Code Remote Development

### 12.1 Install VS Code Extension

1. Open VS Code on your local computer
2. Install extension: **"Remote - SSH"** by Microsoft
3. Click the extension icon or press `F1` and type "Remote-SSH"

### 12.2 Configure SSH Connection

1. Press `F1` in VS Code
2. Type: `Remote-SSH: Add New SSH Host`
3. Enter: `ssh deploy@YOUR_SERVER_IP`
4. Select SSH config file: `~/.ssh/config`

### 12.3 Connect to Server

1. Press `F1`
2. Type: `Remote-SSH: Connect to Host`
3. Select: `YOUR_SERVER_IP`
4. New VS Code window opens
5. Click **"Open Folder"**
6. Navigate to: `/opt/bonifatus-dms`
7. Click **"OK"**

### 12.4 Install Extensions on Remote Server

In the remote VS Code window, install:
- Python
- Docker
- GitLens
- ESLint
- Prettier

### 12.5 Terminal Access in VS Code

1. In VS Code, press `` Ctrl+` `` to open terminal
2. You're now in the server terminal!
3. Run commands directly from VS Code

---

## 13. Backup Strategy

### 13.1 Database Backups (Supabase)

Supabase handles backups automatically. But you can also create manual backups:

```bash
# Create backup script
nano ~/backup-database.sh
```

Paste this:

```bash
#!/bin/bash
BACKUP_DIR="/home/deploy/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Extract database credentials from .env
cd /opt/bonifatus-dms
source .env

# Create backup (if using Supabase, download backup via their dashboard)
# For local PostgreSQL:
# pg_dump $DATABASE_URL > $BACKUP_DIR/backup_$DATE.sql
# gzip $BACKUP_DIR/backup_$DATE.sql

echo "Backup completed: $BACKUP_DIR/backup_$DATE.sql.gz"

# Keep only last 7 backups
ls -t $BACKUP_DIR/backup_*.sql.gz | tail -n +8 | xargs rm -f
```

Save, then:

```bash
chmod +x ~/backup-database.sh
```

### 13.2 Application Backups

Hetzner Backups (enabled during server creation) automatically back up entire server.

**Manual snapshot:**
1. Go to Hetzner Cloud Console
2. Click on your server
3. Go to **"Snapshots"** tab
4. Click **"Create Snapshot"**
5. Name it: `before-major-update-YYYYMMDD`

### 13.3 Automated Backups with Cron

```bash
# Edit crontab
crontab -e

# Add this line (daily backup at 2 AM)
0 2 * * * /home/deploy/backup-database.sh

# Save and exit
```

---

## 14. Access Permissions for Claude Code

To allow me (Claude Code) to help you debug and maintain the system, you can:

### 14.1 Share Server Access

**Option A: Provide SSH Access (Most Control)**

On your server:
```bash
# Add Claude Code's SSH public key (I'll provide this when needed)
nano ~/.ssh/authorized_keys
# Add the key on a new line
```

**Option B: Share Logs Only (Most Secure)**

```bash
# When you need help, export logs:
docker-compose logs > /tmp/logs.txt

# Download to your local computer:
# From your local terminal:
scp deploy@YOUR_SERVER_IP:/tmp/logs.txt .

# Share the logs.txt file with me
```

### 14.2 GitHub Repository Access

Make sure I have access to your GitHub repository:
1. Repository is already public, so I can see the code
2. If you want me to make commits, add a GitHub token to secrets

### 14.3 Environment Variables Access

**Never share actual secret values!** But share the structure:

```bash
# Safe to share (without actual values):
cat .env | sed 's/=.*/=***REDACTED***/g'
```

---

## 15. Troubleshooting

### 15.1 Application Won't Start

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs

# Restart services
docker-compose restart

# Full rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 15.2 SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew --force-renewal

# Reload Nginx
sudo systemctl reload nginx
```

### 15.3 DNS Not Working

```bash
# Check if Nginx is running
sudo systemctl status nginx

# Test DNS resolution
nslookup bonidoc.com

# Check firewall
sudo ufw status
```

### 15.4 Out of Memory

```bash
# Check memory usage
free -h

# Check Docker memory usage
docker stats

# Restart services to free memory
docker-compose restart

# Upgrade server if needed (Hetzner Console > Resize)
```

### 15.5 Database Connection Issues

```bash
# Test database connection
docker-compose exec backend python -c "
from app.database.connection import db_manager
import asyncio
asyncio.run(db_manager.health_check())
"

# Check if DATABASE_URL is correct
cd /opt/bonifatus-dms
grep DATABASE_URL .env
```

### 15.6 Port Already in Use

```bash
# Find what's using port 80/443
sudo lsof -i :80
sudo lsof -i :443

# Kill the process (replace PID with actual process ID)
sudo kill -9 PID

# Or stop Apache if it's running
sudo systemctl stop apache2
sudo systemctl disable apache2
```

---

## Post-Migration Checklist

After completing the migration, verify everything works:

- [ ] Frontend accessible at https://bonidoc.com
- [ ] API accessible at https://api.bonidoc.com/health
- [ ] SSL certificate valid (green padlock in browser)
- [ ] Google OAuth login works
- [ ] Document upload works
- [ ] Document analysis works
- [ ] Categories load properly
- [ ] No CORS errors in browser console
- [ ] Logs are accessible via `docker-compose logs`
- [ ] VS Code Remote SSH works
- [ ] Deployment script `~/deploy.sh` works

---

## Quick Reference Commands

```bash
# === Deployment ===
~/deploy.sh                          # Deploy latest code from GitHub

# === Service Management ===
docker-compose up -d                 # Start services
docker-compose down                  # Stop services
docker-compose restart               # Restart services
docker-compose ps                    # Check service status
docker-compose logs -f               # View live logs

# === Nginx ===
sudo systemctl reload nginx          # Reload Nginx config
sudo nginx -t                        # Test Nginx config
sudo systemctl status nginx          # Check Nginx status

# === SSL Certificates ===
sudo certbot renew                   # Renew certificates
sudo certbot certificates            # List certificates

# === System ===
htop                                 # Monitor resources
docker stats                         # Monitor containers
df -h                                # Check disk space
free -h                              # Check memory

# === Updates ===
sudo apt update && sudo apt upgrade -y   # Update system
docker-compose pull                      # Pull new images
```

---

## Cost Breakdown (Monthly)

| Service | Cost |
|---------|------|
| Hetzner VPS (CPX21) | €8.21 |
| Backups (+20%) | €1.64 |
| Domain (already owned) | €0.00 |
| SSL Certificate (Let's Encrypt) | €0.00 |
| **Total** | **€9.85 (~$10.70/month)** |

Compare to Cloud Run: **~$25-50/month**

**Savings: ~60-80% reduction in hosting costs!**

---

## Next Steps After Migration

1. **Monitor for 24 hours**
   - Check logs regularly
   - Monitor resource usage
   - Test all features

2. **Set up monitoring alerts** (optional)
   - Install Uptime Kuma or similar
   - Get notified if site goes down

3. **Update GitHub Actions**
   - Modify workflow to deploy to Hetzner instead of Cloud Run
   - Use SSH to trigger `~/deploy.sh` on push to main

4. **Optimize performance**
   - Enable Nginx caching
   - Set up CDN (Cloudflare) if needed
   - Optimize Docker images

5. **Security hardening**
   - Set up fail2ban
   - Enable automatic security updates
   - Configure firewall rules

---

## Support

If you encounter any issues during migration:

1. **Check logs first:**
   ```bash
   docker-compose logs -f
   ```

2. **Search for specific errors:**
   ```bash
   docker-compose logs | grep -i error
   ```

3. **Share logs with Claude Code** (redact sensitive info):
   ```bash
   docker-compose logs > logs.txt
   ```

4. **Check this guide's troubleshooting section**

5. **Ask Claude Code** - I'll be here to help you through each step!

---

**Ready to start?** Let's begin with Section 1: Server Selection & Setup!
