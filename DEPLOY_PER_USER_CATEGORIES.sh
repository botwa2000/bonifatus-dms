#!/bin/bash
# Production Deployment Script for Per-User Category Architecture
# Run these commands on Hetzner VPS as root
# Server: 91.99.212.17

set -e  # Exit on error

echo "=========================================="
echo "Per-User Category Architecture Deployment"
echo "=========================================="
echo ""
echo "This deployment will:"
echo "  1. Add Invoices and Taxes categories"
echo "  2. Add French translations to all categories"
echo "  3. Implement per-user category architecture"
echo "  4. Delete all existing test user data"
echo ""
read -p "Press Enter to continue or Ctrl+C to abort..."
echo ""

# Step 1: Backup Database
echo "[Step 1/8] Creating database backup..."
pg_dump -U bonifatus -d bonifatus_dms > backup_per_user_categories_$(date +%Y%m%d_%H%M%S).sql
echo "✓ Backup created"
echo ""

# Step 2: Pull latest code
echo "[Step 2/8] Pulling latest code from GitHub..."
cd /root/bonifatus-dms
git stash  # Stash any local changes
git pull origin main
echo "✓ Code updated"
echo ""

# Step 3: Rebuild backend container
echo "[Step 3/8] Rebuilding backend container..."
docker compose build backend
docker compose up -d backend
sleep 5
echo "✓ Backend rebuilt"
echo ""

# Step 4: Run database migrations
echo "[Step 4/8] Running migration 010 (Invoices + Taxes + French)..."
docker exec bonifatus-backend alembic upgrade head
echo ""
echo "Verifying migrations..."
docker exec bonifatus-backend alembic current
echo "✓ Migration 010 applied"
echo ""

# Step 5: Delete test user data
echo "[Step 5/8] Deleting all test user data for clean slate..."
echo "WARNING: This will delete ALL users and their data!"
read -p "Type 'yes' to confirm: " confirm
if [ "$confirm" != "yes" ]; then
    echo "Aborted"
    exit 1
fi

docker exec -it bonifatus-backend python /app/delete_test_user.py
echo "✓ Test user data deleted"
echo ""

# Step 6: Verify template categories
echo "[Step 6/8] Verifying template categories in database..."
echo ""

echo "Template categories (user_id=NULL):"
docker exec bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT reference_key, name, is_system FROM categories WHERE user_id IS NULL ORDER BY reference_key;"

echo ""
echo "Category translations count:"
docker exec bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT c.reference_key, COUNT(ct.id) as translations
   FROM categories c
   LEFT JOIN category_translations ct ON c.id = ct.category_id
   WHERE c.user_id IS NULL
   GROUP BY c.reference_key
   ORDER BY c.reference_key;"

echo ""
echo "Category keywords count:"
docker exec bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT c.reference_key, COUNT(ck.id) as keywords
   FROM categories c
   LEFT JOIN category_keywords ck ON c.id = ck.category_id
   WHERE c.user_id IS NULL
   GROUP BY c.reference_key
   ORDER BY c.reference_key;"

echo "✓ Template categories verified"
echo ""

# Step 7: Rebuild and restart frontend
echo "[Step 7/8] Rebuilding and restarting frontend..."
cd /root/bonifatus-dms/frontend
npm install
npm run build
pm2 restart bonifatus-frontend
echo "✓ Frontend deployed"
echo ""

# Step 8: Final verification
echo "[Step 8/8] Final verification..."
echo ""

echo "Checking backend health..."
curl -f http://localhost:8000/health || echo "Backend health check failed"

echo ""
echo "Checking user count (should be 0):"
docker exec bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT COUNT(*) FROM users;"

echo ""
echo "Checking user categories count (should be 0):"
docker exec bonifatus-backend psql -U bonifatus -d bonifatus_dms -c \
  "SELECT COUNT(*) FROM categories WHERE user_id IS NOT NULL;"

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Visit https://bonidoc.com and register a new user"
echo "2. User will automatically get 7 personal categories"
echo "3. Test uploading documents in different languages"
echo "4. Test category reset functionality in Settings"
echo "5. Verify document remapping works correctly"
echo ""
echo "Architecture:"
echo "  - Template categories stored with user_id=NULL (7 total)"
echo "  - On registration: all templates copied to user's workspace"
echo "  - Reset: deletes all user categories, re-copies templates"
echo "  - Smart remapping: system docs stay mapped, custom→Other"
echo ""
echo "Monitor logs:"
echo "  Backend:  docker logs -f bonifatus-backend"
echo "  Frontend: pm2 logs bonifatus-frontend"
echo ""
