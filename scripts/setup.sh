#!/bin/bash
# scripts/setup.sh
# Bonifatus DMS - Initial Setup Script
# Automated setup for development and production environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

check_requirements() {
    log_step "Checking system requirements..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3.11+ is required but not installed"
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2)
    if [[ "$(printf '%s\n' "3.11" "$python_version" | sort -V | head -n1)" != "3.11" ]]; then
        log_error "Python 3.11+ is required. Found: $python_version"
        exit 1
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is required but not installed"
        exit 1
    fi
    
    # Check Git
    if ! command -v git &> /dev/null; then
        log_error "Git is required but not installed"
        exit 1
    fi
    
    # Check Docker (optional)
    if command -v docker &> /dev/null; then
        log_info "Docker found: $(docker --version)"
    else
        log_warn "Docker not found - some features may not be available"
    fi
    
    log_info "All required dependencies found ✓"
}

setup_python_environment() {
    log_step "Setting up Python environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "backend/venv" ]; then
        log_info "Creating Python virtual environment..."
        cd backend
        python3 -m venv venv
        cd ..
    fi
    
    # Activate virtual environment
    log_info "Activating virtual environment..."
    source backend/venv/bin/activate
    
    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip
    
    # Install dependencies
    log_info "Installing Python dependencies..."
    cd backend
    pip install -r requirements.txt
    cd ..
    
    log_info "Python environment setup complete ✓"
}

setup_environment_file() {
    log_step "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        log_info "Creating .env file from template..."
        cp .env.example .env
        
        # Generate secret key
        log_info "Generating secure secret key..."
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        
        # Update .env file
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/your-generated-jwt-secret-key-change-in-production/$SECRET_KEY/" .env
        else
            # Linux
            sed -i "s/your-generated-jwt-secret-key-change-in-production/$SECRET_KEY/" .env
        fi
        
        log_warn "⚠️  IMPORTANT: Update .env file with your actual credentials:"
        log_warn "   - DATABASE_URL (Supabase connection string)"
        log_warn "   - GOOGLE_CLIENT_ID (Google OAuth client ID)"
        log_warn "   - GOOGLE_CLIENT_SECRET (Google OAuth client secret)"
        log_warn "   - GCP_PROJECT (Google Cloud project ID)"
    else
        log_info ".env file already exists ✓"
    fi
}

setup_database() {
    log_step "Setting up database..."
    
    # Source environment variables
    if [ -f ".env" ]; then
        set -a
        source .env
        set +a
    fi
    
    # Check if DATABASE_URL is configured
    if [[ -z "${DATABASE_URL}" || "${DATABASE_URL}" == *"your-supabase-connection-string"* ]]; then
        log_warn "DATABASE_URL not configured. Skipping database setup."
        log_warn "Please update .env with your Supabase connection string and run:"
        log_warn "  cd backend && python -m alembic upgrade head"
        return
    fi
    
    # Run database migrations
    log_info "Running database migrations..."
    cd backend
    source venv/bin/activate
    python -m alembic upgrade head
    cd ..
    
    log_info "Database setup complete ✓"
}

setup_git_hooks() {
    log_step "Setting up Git hooks..."
    
    # Create pre-commit hook
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook for Bonifatus DMS
# Runs linting and basic tests before commit

cd backend

# Activate virtual environment
source venv/bin/activate

# Run linting
echo "Running code formatting checks..."
black --check src || {
    echo "Code formatting issues found. Run 'black src' to fix."
    exit 1
}

# Run flake8
echo "Running linting..."
flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics || {
    echo "Linting issues found. Please fix before committing."
    exit 1
}

echo "Pre-commit checks passed!"
EOF

    chmod +x .git/hooks/pre-commit
    log_info "Git hooks setup complete ✓"
}

setup_development_tools() {
    log_step "Setting up development tools..."
    
    cd backend
    source venv/bin/activate
    
    # Install development dependencies
    log_info "Installing development tools..."
    pip install black flake8 pytest pytest-cov pytest-asyncio
    
    cd ..
    log_info "Development tools setup complete ✓"
}

run_tests() {
    log_step "Running initial tests..."
    
    cd backend
    source venv/bin/activate
    
    # Set test environment variables
    export APP_ENVIRONMENT=testing
    export DATABASE_URL=sqlite:///./test_bonifatus.db
    export SECURITY_SECRET_KEY=test-secret-key
    export GOOGLE_CLIENT_ID=test-client-id
    export GOOGLE_CLIENT_SECRET=test-client-secret
    
    # Run tests
    log_info "Running test suite..."
    pytest tests/ -v --tb=short
    
    cd ..
    log_info "Tests completed ✓"
}

display_next_steps() {
    log_step "Setup completed successfully! 🎉"
    echo
    log_info "Next steps:"
    echo "  1. Update .env file with your actual credentials:"
    echo "     - Supabase database URL"
    echo "     - Google OAuth client ID and secret"
    echo "     - Google Cloud project ID"
    echo
    echo "  2. Start the development server:"
    echo "     cd backend"
    echo "     source venv/bin/activate"
    echo "     python -m uvicorn src.main:app --reload"
    echo
    echo "  3. Access the API:"
    echo "     - API: http://localhost:8000"
    echo "     - Docs: http://localhost:8000/api/docs"
    echo "     - Health: http://localhost:8000/health"
    echo
    echo "  4. Set up GitHub Secrets for deployment:"
    echo "     - GCP_PROJECT"
    echo "     - GCP_SA_KEY"
    echo "     - DATABASE_URL"
    echo "     - GOOGLE_CLIENT_ID"
    echo "     - GOOGLE_CLIENT_SECRET"
    echo "     - SECURITY_SECRET_KEY"
    echo
    log_info "Documentation: https://github.com/yourusername/bonifatus-dms"
    log_info "Support: Create an issue on GitHub"
}

cleanup_on_error() {
    log_error "Setup failed! Cleaning up..."
    # Add cleanup logic here if needed
    exit 1
}

# Main execution
main() {
    echo "🚀 Bonifatus DMS Setup Script"
    echo "============================="
    echo
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    # Parse command line arguments
    SKIP_TESTS=false
    SKIP_HOOKS=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --skip-hooks)
                SKIP_HOOKS=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo
                echo "Options:"
                echo "  --skip-tests    Skip running tests"
                echo "  --skip-hooks    Skip setting up Git hooks"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Run setup steps
    check_requirements
    setup_python_environment
    setup_environment_file
    setup_development_tools
    
    if [ "$SKIP_HOOKS" = false ]; then
        setup_git_hooks
    fi
    
    setup_database
    
    if [ "$SKIP_TESTS" = false ]; then
        run_tests
    fi
    
    display_next_steps
}

# Run main function
main "$@"