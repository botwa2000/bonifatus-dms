#!/bin/bash
#
# Development Environment Setup Script
# Run this on the Hetzner server to complete dev environment setup
#
# Usage: ./setup_dev_environment.sh
#

set -e

echo "======================================================================"
echo "BONIFATUS DMS - Development Environment Setup"
echo "======================================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEV_DIR="/opt/bonifatus-dms-dev"
DEV_DB="bonifatus_dms_dev"
DEV_DB_USER="bonifatus_dev"
DEV_DB_PASS="BoniDocDev2025Password"

echo -e "${GREEN}Step 1: Checking dev containers...${NC}"
cd $DEV_DIR

# Stop any existing containers
echo "Stopping existing dev containers..."
docker compose down 2>/dev/null || true

# Build and start fresh
echo "Building dev containers..."
docker compose build

echo "Starting dev containers..."
docker compose up -d

echo ""
echo -e "${GREEN}Step 2: Waiting for containers to be healthy...${NC}"
sleep 10

# Check container status
docker compose ps

echo ""
echo -e "${GREEN}Step 3: Populating development database...${NC}"

# Wait for backend to be fully ready
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if docker exec bonifatus-backend-dev curl -f http://localhost:8080/health >/dev/null 2>&1; then
        echo "✓ Backend is healthy!"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

# Run database population scripts
echo "Running populate_defaults.py..."
docker exec bonifatus-backend-dev python3 /app/populate_defaults.py

echo "Running populate_keywords.py..."
docker exec bonifatus-backend-dev python3 /app/populate_keywords.py

echo "Running populate_ml_data.py..."
docker exec bonifatus-backend-dev python3 /app/populate_ml_data.py || echo "ML data population skipped (optional)"

echo ""
echo -e "${GREEN}Step 4: Verifying setup...${NC}"

# Check database
echo "Checking database..."
PGPASSWORD=$DEV_DB_PASS psql -h localhost -U $DEV_DB_USER -d $DEV_DB -c "SELECT COUNT(*) as categories FROM categories;" 2>/dev/null || echo "⚠️  Database check failed (check manually)"

# Check API health
echo "Checking backend API..."
curl -s http://localhost:8081/health | python3 -m json.tool || echo "⚠️  Backend not responding on port 8081"

# Check frontend
echo "Checking frontend..."
curl -s -I http://localhost:3001 | head -1 || echo "⚠️  Frontend not responding on port 3001"

echo ""
echo "======================================================================"
echo -e "${GREEN}Development Environment Setup Complete!${NC}"
echo "======================================================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Add DNS records in Cloudflare:"
echo "   - dev.bonidoc.com → A → 91.99.212.17 (Proxied)"
echo "   - api-dev.bonidoc.com → A → 91.99.212.17 (Proxied)"
echo ""
echo "2. Add Google OAuth redirect URI:"
echo "   https://api-dev.bonidoc.com/api/v1/auth/google/callback"
echo ""
echo "3. Wait for DNS propagation (5-10 minutes)"
echo ""
echo "4. Test access:"
echo "   - https://dev.bonidoc.com"
echo "   - https://api-dev.bonidoc.com/health"
echo ""
echo "======================================================================"
echo ""
echo "📊 Container Status:"
docker ps | grep -E "(CONTAINER|dev)"
echo ""
echo "🔧 Useful Commands:"
echo "  View logs:    cd $DEV_DIR && docker compose logs -f"
echo "  Restart:      cd $DEV_DIR && docker compose restart"
echo "  Stop:         cd $DEV_DIR && docker compose down"
echo "  Rebuild:      cd $DEV_DIR && docker compose build && docker compose up -d"
echo ""
