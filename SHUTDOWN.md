# BoniDoc DMS — Shutdown & Revival Guide

**Shutdown date:** 2026-05-16  
**Reason:** Site taken offline; infrastructure preserved for potential restart.  
**Code repo:** https://github.com/botwa2000/bonifatus-dms (main branch — complete and up to date)  
**Local backup dir:** `C:\Users\Alexa\bonifatus-shutdown-backup\` (DB dumps + secrets files)

---

## 1. What Was Running

**BoniDoc DMS** — a document management system hosted at **bonidoc.com**.

### Services (Docker Swarm)

| Service | Image | Prod Port | Dev Port | Description |
|---------|-------|-----------|----------|-------------|
| backend | bonifatus-backend:latest | 8080 | 8081 | FastAPI REST API |
| frontend | bonifatus-frontend:latest | 3000 | 3001 | Next.js web app |
| celery-worker | bonifatus-celery-worker:latest | — | — | Async task worker |
| libretranslate | libretranslate/libretranslate | 5000 (internal) | 5001 (internal) | Translation engine |
| redis | redis:7-alpine | 6379 (internal) | 6380 (internal) | Celery broker/cache |

### Docker Stacks

| Stack | Dir on server | Compose file |
|-------|--------------|--------------|
| `bonifatus` (prod) | `/opt/bonifatus-dms` | `docker-compose.yml` |
| `bonifatus-dev` (dev) | `/opt/bonifatus-dms-dev` | `docker-compose-dev.yml` |

---

## 2. Infrastructure

### Hetzner Server

- **Name:** bonidoc-server
- **IP:** 91.99.212.17
- **Plan:** CPX22 (2 vCPU, 4 GB RAM, 80 GB SSD) — ~€6.49–7.59/month
- **OS:** Ubuntu 24.04.3 LTS
- **SSH:** `ssh root@91.99.212.17` (key: `~/.ssh/id_rsa`)

### Domains (Cloudflare)

| Domain | Points to | Environment |
|--------|-----------|-------------|
| bonidoc.com | 91.99.212.17 (via Cloudflare proxy) | Production frontend |
| www.bonidoc.com | 91.99.212.17 | Production frontend |
| api.bonidoc.com | 91.99.212.17 | Production API |
| dev.bonidoc.com | 91.99.212.17 | Dev frontend (IP-whitelisted) |
| api-dev.bonidoc.com | 91.99.212.17 | Dev API (IP-whitelisted) |

**Cloudflare account:** Set to Full (Strict) SSL mode. All bonidoc.com records proxied.

### SSL/TLS

Cloudflare Origin Certificates (not Let's Encrypt):
- Cert: `/etc/ssl/cloudflare/bonidoc.com.pem`
- Key: `/etc/ssl/cloudflare/bonidoc.com.key`

New origin certs can be generated in Cloudflare dashboard → SSL/TLS → Origin Server → Create Certificate.

### Nginx (on server)

Configs in `/etc/nginx/sites-enabled/`:
- `bonidoc.com` — proxies ports 3000 (frontend) and 8080 (API)
- `dev.bonidoc.com` — proxies ports 3001 / 8081, IP-whitelisted

---

## 3. Database

**PostgreSQL 16** — local installation on same Hetzner server.

### Production Database

| Setting | Value |
|---------|-------|
| Database | bonifatus_dms |
| User | bonifatus |
| Password | BoniDoc2025SecurePassword |
| Host | localhost:5432 (host) / host.docker.internal:5432 (Docker) |
| SSL | Enabled (self-signed cert) |

### Development Database

| Setting | Value |
|---------|-------|
| Database | bonifatus_dms_dev |
| User | bonifatus_dev |
| Password | BoniDocDev2025Password |
| Host | localhost:5432 |

### Schema Summary (30 tables)

Categories, documents, document_analysis, users, subscriptions, campaigns, campaign_recipients, keywords, translations, stop_words, ngram_patterns, system_settings, and more. Full schema in Alembic migrations: `backend/alembic/versions/`.

### DB Backup Location

SQL dumps saved at shutdown: `C:\Users\Alexa\bonifatus-shutdown-backup\`
- `bonifatus_dms.sql` — full production database dump
- `bonifatus_dms_dev.sql` — full dev database dump

---

## 4. Docker Swarm Secrets

Secrets were managed via Docker Swarm (`docker secret create`). Secret files were also stored at `/opt/bonifatus-secrets/` on the server (deleted at shutdown). The local backup is at `C:\Users\Alexa\bonifatus-shutdown-backup\secrets_prod\` and `secrets_dev\`.

### Prod secrets (suffix `_prod`)

| Secret | Purpose |
|--------|---------|
| database_url_v2_prod | PostgreSQL connection string |
| security_secret_key_prod | JWT signing key |
| encryption_key_prod | Fernet encryption key for stored credentials |
| google_client_id_prod | Google OAuth client ID |
| google_client_secret_prod | Google OAuth client secret |
| onedrive_client_id_prod | OneDrive OAuth client ID |
| onedrive_client_secret_prod | OneDrive OAuth client secret |
| facebook_client_id_prod | Facebook OAuth client ID |
| facebook_client_secret_prod | Facebook OAuth client secret |
| gcp_project_prod | GCP project name (for Google Drive) |
| brevo_api_key_prod | Brevo (Sendinblue) transactional email API key |
| imap_password_prod | IMAP mailbox password for inbound email |
| stripe_secret_key_prod | Stripe secret key |
| stripe_publishable_key_prod | Stripe publishable key |
| stripe_webhook_secret_prod | Stripe webhook signing secret |
| turnstile_secret_key_prod | Cloudflare Turnstile CAPTCHA secret |

Dev secrets are the same names with `_dev` suffix.

### Legacy unsuffixed secrets (also removed)

`database_url`, `encryption_key`, `security_secret_key`, `google_client_id`, `google_client_secret`, `gcp_project`, `brevo_api_key`, `imap_password`, `onedrive_client_id`, `onedrive_client_secret`, `stripe_secret_key`, `stripe_publishable_key`, `stripe_webhook_secret`, `turnstile_secret_key`

---

## 5. Application Directory Structure

```
/opt/bonifatus-dms/             ← Production
├── backend/                    ← FastAPI app (Python)
│   ├── app/
│   ├── alembic/                ← DB migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   ← Next.js app (TypeScript)
│   ├── src/
│   └── Dockerfile
├── secrets/                    ← Google Drive service account key
│   └── google-drive-key.json
├── docker-compose.yml          ← Prod swarm compose
└── .git/

/opt/bonifatus-dms-dev/         ← Development (mirror of above)
├── docker-compose-dev.yml

/opt/bonifatus-secrets/         ← Secret files (text, chmod 600)
├── prod/                       ← One file per secret (e.g., database_url)
└── dev/
```

---

## 6. Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14+, React, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python 3.11), SQLAlchemy, Alembic |
| Task Queue | Celery + Redis |
| Database | PostgreSQL 16 |
| Translation | LibreTranslate (self-hosted) |
| Auth | Google OAuth, Facebook OAuth, OneDrive OAuth, JWT sessions |
| Payments | Stripe |
| Email | Brevo (transactional) + IMAP (inbound) |
| Storage | Google Drive, OneDrive (per-user cloud storage) |
| Containerization | Docker Swarm (single-node) |
| Web server | Nginx (reverse proxy) |
| CDN/DNS | Cloudflare (Full Strict SSL) |
| Monitoring | PostHog (EU endpoint), Google Analytics |
| CAPTCHA | Cloudflare Turnstile |
| ML | spaCy (NLP), ClamAV (malware scan) |

---

## 7. Revival Instructions (Step by Step)

### Prerequisites

1. Have a Hetzner server running Ubuntu 24.04 (or reuse the same one if not deleted)
2. DNS records pointing to server IP in Cloudflare
3. The git repo cloned on the server
4. All secret values available (see backup directory)
5. Docker installed

### Step 1 — Server Setup

```bash
ssh root@<SERVER_IP>

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Nginx
apt install -y nginx

# Initialize Docker Swarm
docker swarm init --advertise-addr 127.0.0.1
```

### Step 2 — Clone Repositories

```bash
# Production
git clone https://github.com/botwa2000/bonifatus-dms.git /opt/bonifatus-dms

# Dev
git clone https://github.com/botwa2000/bonifatus-dms.git /opt/bonifatus-dms-dev
```

### Step 3 — Restore PostgreSQL

```bash
# Install PostgreSQL 16
apt install -y postgresql-16

# Create databases and users
sudo -u postgres psql <<'SQL'
CREATE USER bonifatus WITH PASSWORD 'BoniDoc2025SecurePassword';
CREATE DATABASE bonifatus_dms OWNER bonifatus;
CREATE USER bonifatus_dev WITH PASSWORD 'BoniDocDev2025Password';
CREATE DATABASE bonifatus_dms_dev;
GRANT ALL ON DATABASE bonifatus_dms_dev TO bonifatus_dev;
SQL

# Restore from backup (copy SQL files to server first)
scp bonifatus_dms.sql root@<SERVER_IP>:/tmp/
scp bonifatus_dms_dev.sql root@<SERVER_IP>:/tmp/
ssh root@<SERVER_IP> "sudo -u postgres psql bonifatus_dms < /tmp/bonifatus_dms.sql"
ssh root@<SERVER_IP> "sudo -u postgres psql bonifatus_dms_dev < /tmp/bonifatus_dms_dev.sql"
```

### Step 4 — Restore Docker Secrets

Copy secret files from `C:\Users\Alexa\bonifatus-shutdown-backup\secrets_prod\` back to server, then:

```bash
# On server, in the directory containing secret files:
for secret_file in *; do
    docker secret create "${secret_file}_prod" "$secret_file"
done

# Repeat for dev secrets with _dev suffix
```

Or create secrets manually:
```bash
echo -n "value" | docker secret create secret_name -
```

### Step 5 — Cloudflare Origin Certificate

1. Cloudflare dashboard → bonidoc.com → SSL/TLS → Origin Server → Create Certificate
2. Save cert as `/etc/ssl/cloudflare/bonidoc.com.pem`
3. Save key as `/etc/ssl/cloudflare/bonidoc.com.key`
4. `chmod 600 /etc/ssl/cloudflare/bonidoc.com.key`

### Step 6 — Nginx Configuration

Copy nginx configs from the repository:
- `nginx-dev-ip-whitelist.conf` → adapt and copy to `/etc/nginx/sites-available/dev.bonidoc.com`
- Create similar config for `bonidoc.com` (production, port 3000/8080)
- Symlink to `sites-enabled/`
- `nginx -t && systemctl reload nginx`

### Step 7 — Deploy

```bash
ssh root@<SERVER_IP> 'cd /opt/bonifatus-dms && \
  docker compose build && \
  docker stack deploy -c docker-compose.yml bonifatus && \
  sleep 40 && \
  CONTAINER=$(docker ps | grep bonifatus_backend | head -1 | cut -d" " -f1) && \
  docker exec $CONTAINER alembic upgrade head'
```

See `DEPLOY.md` for full deployment reference.

---

## 8. External Services to Re-enable

| Service | Action needed |
|---------|--------------|
| Google OAuth | Verify redirect URIs in Google Cloud Console (GCP project) |
| Facebook OAuth | Re-enable app in Facebook Developers (App ID: 1440613847708620) |
| OneDrive OAuth | Verify redirect URIs in Azure portal |
| Stripe | Re-enable webhook endpoint in Stripe dashboard |
| Cloudflare Turnstile | Verify site domain in Cloudflare Turnstile settings |
| Brevo | No action needed (API key-based) |
| PostHog | No action needed (key-based) |
| Google Analytics | No action needed (key-based) |

---

## 9. What Was NOT Deleted

The following remain intact and unaffected:
- **GitHub repository:** https://github.com/botwa2000/bonifatus-dms (code + full history)
- **Local codebase:** `C:\Users\Alexa\bonifatus-dms\`
- **Hetzner server** (if not deleted in Hetzner console — just cleaned of bonifatus data)
- **TaxAlex project** on same server (completely untouched): taxalex, taxalex-dev stacks, taxalex/taxalex_dev databases, taxalex domains and secrets
- **Cloudflare DNS records** (were left in place; can be proxied/unproxied as needed)

---

## 10. What Was Deleted from the Server

- Docker stacks: `bonifatus` and `bonifatus-dev`
- Docker images: `bonifatus-backend`, `bonifatus-frontend`, `bonifatus-celery-worker` (and dev variants)
- Docker secrets: all non-taxalex secrets (full list in §4)
- Directories: `/opt/bonifatus-dms`, `/opt/bonifatus-dms-dev`, `/opt/bonifatus-secrets`
- PostgreSQL: databases `bonifatus_dms` and `bonifatus_dms_dev`, users `bonifatus` and `bonifatus_dev`
- Nginx virtual hosts: `bonidoc.com` and `dev.bonidoc.com`
- SSL/TLS: `/etc/ssl/cloudflare/bonidoc.com.pem` and `bonidoc.com.key`
