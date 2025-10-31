#!/bin/bash
# Production Deployment Script for Multi-Language Feature
# Run these commands on Hetzner VPS as root or with sudo

set -e  # Exit on error

echo "=========================================="
echo "Multi-Language Feature Deployment"
echo "=========================================="
echo ""

# Step 1: Backup Database
echo "[Step 1/7] Creating database backup..."
pg_dump -U bonifatus -d bonifatus_dms > backup_multilingual_$(date +%Y%m%d_%H%M%S).sql
echo "✓ Backup created"
echo ""

# Step 2: Pull latest code
echo "[Step 2/7] Pulling latest code from GitHub..."
cd /root/bonifatus-dms
git pull origin main
echo "✓ Code updated"
echo ""

# Step 3: Restart backend
echo "[Step 3/7] Restarting backend service..."
docker-compose restart backend
sleep 5
echo "✓ Backend restarted"
echo ""

# Step 4: Run database migrations
echo "[Step 4/7] Running database migrations..."
docker exec bonifatus-backend alembic upgrade head
echo ""
echo "Verifying migrations..."
docker exec bonifatus-backend alembic current
echo "✓ Migrations applied"
echo ""

# Step 5: Add French support
echo "[Step 5/7] Adding French language support..."
docker exec bonifatus-backend python /app/add_french_stopwords.py
echo ""
docker exec bonifatus-backend python /app/update_supported_languages.py
echo "✓ French support added"
echo ""

# Step 6: Build and restart frontend
echo "[Step 6/7] Building and restarting frontend..."
cd /root/bonifatus-dms/frontend
npm install
npm run build
pm2 restart bonifatus-frontend
echo "✓ Frontend deployed"
echo ""

# Step 7: Verification
echo "[Step 7/7] Running verification checks..."
echo ""

echo "Checking preferred_doc_languages column..."
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='preferred_doc_languages';"

echo ""
echo "Checking language metadata..."
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT setting_key FROM system_settings WHERE setting_key = 'language_metadata';"

echo ""
echo "Checking French stop words..."
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT COUNT(*) FROM stop_words WHERE language_code = 'fr';"

echo ""
echo "Checking supported languages..."
docker exec -it bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT setting_value FROM system_settings WHERE setting_key = 'supported_languages';"

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Test at https://bonidoc.com/settings"
echo "2. Verify document language checkboxes appear"
echo "3. Upload a French document and check language warning"
echo "4. Monitor logs: docker logs -f bonifatus-backend"
echo ""
