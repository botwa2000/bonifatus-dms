# backend/tests/conftest.py
"""
Bonifatus DMS - Test Configuration
Pytest fixtures and configuration for comprehensive testing
"""

import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import tempfile
import os

from src.main import app
from src.database.models import Base, User, Category, UserTier
from src.database.connection import get_db
from src.core.config import get_settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Override settings for testing"""
    with patch.object(get_settings, '__call__') as mock_settings:
        mock_settings.return_value.database.database_url = "sqlite:///./test.db"
        mock_settings.return_value.security.secret_key = "test-secret-key"
        mock_settings.return_value.app.environment = "testing"
        mock_settings.return_value.google.google_client_id = "test-client-id"
        mock_settings.return_value.google.google_client_secret = "test-client-secret"
        yield mock_settings.return_value


@pytest.fixture(scope="function")
def test_db_engine():
    """Create a test database engine"""
    engine = create_engine(
        "sqlite:///./test_bonifatus.db",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
        echo=False
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_bonifatus.db")
    except FileNotFoundError:
        pass


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create a test database session"""
    TestingSessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=test_db_engine
    )
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(test_db_session):
    """Create a test client with database override"""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(test_db_session):
    """Create a test user"""
    user = User(
        google_id="test_google_id_123",
        email="test@example.com",
        full_name="Test User",
        tier=UserTier.FREE,
        is_active=True,
        is_verified=True
    )
    
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    
    return user


@pytest.fixture(scope="function")
def test_premium_user(test_db_session):
    """Create a premium test user"""
    user = User(
        google_id="test_premium_google_id_456",
        email="premium@example.com",
        full_name="Premium Test User",
        tier=UserTier.PREMIUM,
        is_active=True,
        is_verified=True,
        google_drive_connected=True
    )
    
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    
    return user


@pytest.fixture(scope="function")
def test_admin_user(test_db_session):
    """Create an admin test user"""
    user = User(
        google_id="test_admin_google_id_789",
        email="admin@example.com",
        full_name="Admin Test User",
        tier=UserTier.ADMIN,
        is_active=True,
        is_verified=True
    )
    
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    
    return user


@pytest.fixture(scope="function")
def test_category(test_db_session, test_user):
    """Create a test category"""
    category = Category(
        user_id=test_user.id,
        name_en="Test Category",
        name_de="Test Kategorie",
        description_en="Test category description",
        description_de="Test Kategorie Beschreibung",
        color="#FF5733",
        keywords="test,category,example",
        is_system_category=False
    )
    
    test_db_session.add(category)
    test_db_session.commit()
    test_db_session.refresh(category)
    
    return category

@pytest.fixture(scope="function")
def test_document(test_db_session, test_user, test_category):
    """Create a test document"""
    from src.database.models import Document, DocumentStatus
    
    document = Document(
        user_id=test_user.id,
        category_id=test_category.id,
        filename="test_document.pdf",
        original_filename="Original Test Document.pdf",
        file_path="/Test Category/test_document.pdf",
        google_drive_file_id="test_file_id_123",
        file_size_bytes=1024000,
        mime_type="application/pdf",
        file_extension=".pdf",
        status=DocumentStatus.READY,
        title="Test Document",
        description="Test document description"
    )
    
    test_db_session.add(document)
    test_db_session.commit()
    test_db_session.refresh(document)
    
    return document

@pytest.fixture(scope="function")
def mock_google_drive():
    """Mock Google Drive client"""
    with patch('src.integrations.google_drive.GoogleDriveClient') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        
        # Configure mock methods
        mock_instance.check_connection.return_value = {
            "connected": True,
            "user_email": "test@example.com",
            "storage_quota": {
                "limit": 15000000000,  # 15GB
                "usage": 1000000000,   # 1GB
                "usage_in_drive": 500000000  # 500MB
            }
        }
        
        mock_instance.upload_file.return_value = {
            "file_id": "test_file_id_123",
            "file_path": "/Test Category/test_document.pdf",
            "file_size": 1024000,
            "created_time": "2024-01-01T12:00:00Z",
            "web_view_link": "https://drive.google.com/file/d/test_file_id_123/view"
        }
        
        mock_instance.initialize_user_folder.return_value = True
        mock_instance.delete_file.return_value = True
        mock_instance.get_download_url.return_value = "https://drive.google.com/uc?id=test_file_id_123"
        
        yield mock_instance


@pytest.fixture(scope="function")
def mock_google_oauth():
    """Mock Google OAuth service"""
    with patch('src.services.google_oauth_service.GoogleOAuthService') as mock_service:
        mock_instance = Mock()
        mock_service.return_value = mock_instance
        
        # Configure mock methods
        mock_instance.get_authorization_url.return_value = (
            "https://accounts.google.com/oauth2/auth?client_id=test",
            "test_state_token"
        )
        
        mock_instance.verify_state.return_value = True
        
        mock_instance.exchange_code_for_tokens.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/drive.file"
        }
        
        mock_instance.get_user_info.return_value = {
            "id": "test_google_id_123",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "verified_email": True
        }
        
        yield mock_instance


@pytest.fixture(scope="function")
def auth_headers(test_user):
    """Create authentication headers for test user"""
    from src.services.auth_service import AuthService
    from unittest.mock import Mock
    
    # Mock JWT token
    mock_token = "test.jwt.token"
    
    return {"Authorization": f"Bearer {mock_token}"}


@pytest.fixture(scope="function")
def temp_file():
    """Create a temporary file for testing uploads"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(b"Test PDF content for upload testing")
        tmp_file_path = tmp_file.name
    
    yield tmp_file_path
    
    # Cleanup
    try:
        os.unlink(tmp_file_path)
    except FileNotFoundError:
        pass


@pytest.fixture(scope="function", autouse=True)
def clean_test_data():
    """Automatically clean up test data after each test"""
    yield
    
    # Cleanup any test files created during testing
    test_files = [f for f in os.listdir('.') if f.startswith('test_') and f.endswith('.db')]
    for test_file in test_files:
        try:
            os.remove(test_file)
        except FileNotFoundError:
            pass


# Custom pytest markers
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as authentication related"
    )
    config.addinivalue_line(
        "markers", "google_drive: mark test as Google Drive related"
    )


# Test data fixtures
@pytest.fixture
def sample_document_data():
    """Sample document data for testing"""
    return {
        "filename": "test_document.pdf",
        "original_filename": "Original Test Document.pdf",
        "title": "Test Document Title",
        "description": "This is a test document for unit testing",
        "mime_type": "application/pdf",
        "file_size_bytes": 1024000,
        "file_extension": ".pdf"
    }


@pytest.fixture
def sample_category_data():
    """Sample category data for testing"""
    return {
        "name_en": "Test Category",
        "name_de": "Test Kategorie", 
        "description_en": "English description",
        "description_de": "Deutsche Beschreibung",
        "color": "#FF5733",
        "keywords": "test,category,sample"
    }