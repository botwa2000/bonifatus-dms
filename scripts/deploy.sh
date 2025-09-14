#!/bin/bash
# scripts/deploy.sh
# Bonifatus DMS - Deployment Script
# Production deployment to Google Cloud Run

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GCP_PROJECT:-"bon-dms"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="bon-dms-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
ENVIRONMENT=${ENVIRONMENT:-"production"}

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking deployment requirements..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud. Please run 'gcloud auth login'"
        exit 1
    fi
    
    log_info "All requirements satisfied ✓"
}

verify_environment() {
    log_info "Verifying environment variables..."
    
    required_vars=(
        "DATABASE_URL"
        "GOOGLE_CLIENT_ID" 
        "GOOGLE_CLIENT_SECRET"
        "SECURITY_SECRET_KEY"
    )
    
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -ne 0 ]]; then
        log_error "Missing required environment variables:"
        printf '%s\n' "${missing_vars[@]}"
        log_error "Please set these variables and try again."
        exit 1
    fi
    
    log_info "Environment variables verified ✓"
}

build_image() {
    log_info "Building Docker image..."
    
    # Build the image
    cd backend
    docker build -t $IMAGE_NAME:latest -t $IMAGE_NAME:$GITHUB_SHA .
    cd ..
    
    log_info "Docker image built successfully ✓"
}

push_image() {
    log_info "Pushing image to Google Container Registry..."
    
    # Configure Docker for GCR
    gcloud auth configure-docker --quiet
    
    # Push the image
    docker push $IMAGE_NAME:latest
    docker push $IMAGE_NAME:$GITHUB_SHA
    
    log_info "Image pushed successfully ✓"
}

deploy_to_cloud_run() {
    log_info "Deploying to Cloud Run..."
    
    # Determine service name based on branch
    BRANCH_NAME=${GITHUB_REF_NAME:-"main"}
    FULL_SERVICE_NAME="${SERVICE_NAME}-${BRANCH_NAME}"
    
    # Deploy to Cloud Run
    gcloud run deploy $FULL_SERVICE_NAME \
        --image=$IMAGE_NAME:${GITHUB_SHA:-latest} \
        --platform=managed \
        --region=$REGION \
        --allow-unauthenticated \
        --memory=1Gi \
        --cpu=1 \
        --port=8000 \
        --max-instances=10 \
        --timeout=300 \
        --set-env-vars="APP_ENVIRONMENT=${ENVIRONMENT}" \
        --set-env-vars="DATABASE_URL=${DATABASE_URL}" \
        --set-env-vars="GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}" \
        --set-env-vars="GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}" \
        --set-env-vars="SECURITY_SECRET_KEY=${SECURITY_SECRET_KEY}" \
        --set-env-vars="CORS_ORIGINS=https://${FULL_SERVICE_NAME}-*.run.app" \
        --quiet
    
    # Get the deployed URL
    SERVICE_URL=$(gcloud run services describe $FULL_SERVICE_NAME --platform=managed --region=$REGION --format="value(status.url)")
    
    log_info "Deployment completed successfully ✓"
    log_info "Service URL: $SERVICE_URL"
}

run_health_check() {
    log_info "Running health check..."
    
    # Wait a moment for service to be ready
    sleep 10
    
    # Get service URL
    FULL_SERVICE_NAME="${SERVICE_NAME}-${GITHUB_REF_NAME:-main}"
    SERVICE_URL=$(gcloud run services describe $FULL_SERVICE_NAME --platform=managed --region=$REGION --format="value(status.url)")
    
    # Health check
    if curl -f --max-time 30 "${SERVICE_URL}/health" > /dev/null 2>&1; then
        log_info "Health check passed ✓"
        log_info "Service is healthy and ready to serve traffic"
    else
        log_error "Health check failed ✗"
        log_error "Service may not be responding correctly"
        exit 1
    fi
}

run_database_migration() {
    log_info "Running database migrations..."
    
    # Run migrations in a temporary Cloud Run job
    gcloud run jobs create migration-job-$(date +%s) \
        --image=$IMAGE_NAME:${GITHUB_SHA:-latest} \
        --region=$REGION \
        --task-timeout=600 \
        --max-retries=1 \
        --set-env-vars="DATABASE_URL=${DATABASE_URL}" \
        --command="python" \
        --args="-m,alembic,upgrade,head" \
        --execute-now \
        --wait
    
    log_info "Database migrations completed ✓"
}

cleanup() {
    log_info "Cleaning up temporary resources..."
    
    # Remove old images (keep last 5)
    gcloud container images list-tags $IMAGE_NAME \
        --limit=999999 \
        --sort-by=TIMESTAMP \
        --filter="timestamp.date('%Y-%m-%d')<=$(date -d '30 days ago' '+%Y-%m-%d')" \
        --format="get(digest)" | \
    while read digest; do
        if [[ -n "$digest" ]]; then
            gcloud container images delete "${IMAGE_NAME}@${digest}" --quiet || true
        fi
    done
    
    log_info "Cleanup completed ✓"
}

main() {
    log_info "Starting Bonifatus DMS deployment..."
    log_info "Project: $PROJECT_ID"
    log_info "Region: $REGION" 
    log_info "Environment: $ENVIRONMENT"
    
    check_requirements
    verify_environment
    build_image
    push_image
    
    # Run migrations before deployment
    if [[ "$ENVIRONMENT" == "production" ]]; then
        run_database_migration
    fi
    
    deploy_to_cloud_run
    run_health_check
    cleanup
    
    log_info "🎉 Deployment completed successfully!"
    log_info "Your Bonifatus DMS API is now live and ready to serve traffic."
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project)
            PROJECT_ID="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --skip-migrations)
            SKIP_MIGRATIONS=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --project PROJECT_ID    Google Cloud Project ID"
            echo "  --region REGION         Deployment region (default: us-central1)"
            echo "  --environment ENV       Environment (development/staging/production)"
            echo "  --skip-migrations       Skip database migrations"
            echo "  --help                  Show this help message"
            echo ""
            echo "Required environment variables:"
            echo "  DATABASE_URL            Supabase database connection string"
            echo "  GOOGLE_CLIENT_ID        Google OAuth client ID"
            echo "  GOOGLE_CLIENT_SECRET    Google OAuth client secret"
            echo "  SECURITY_SECRET_KEY     JWT secret key"
            echo ""
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            log_error "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main deployment
main