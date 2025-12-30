"""
Pytest configuration and shared fixtures
"""
import pytest
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture(scope="session")
def app_root():
    """Get application root directory"""
    return Path(__file__).parent.parent


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing"""
    return "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def sample_provider_keys():
    """Sample provider keys for testing"""
    return ['google_drive', 'onedrive', 'dropbox', 'box']
