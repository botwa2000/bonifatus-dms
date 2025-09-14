# backend/tests/test_auth.py
"""
Bonifatus DMS - Authentication Tests
Comprehensive tests for authentication and authorization
"""

import pytest
from unittest.mock import patch, Mock
from fastapi import status

from src.services.auth_service import AuthService
from src.database.models import User, UserTier


@pytest.mark.auth
class TestGoogleOAuth:
    """Test Google OAuth authentication flow"""
    
    def test_google_login_initiate(self, client):
        """Test initiating Google OAuth login"""
        with patch('src.api.auth.GoogleOAuthService') as mock_oauth:
            mock_oauth_instance = Mock()
            mock_oauth.return_value = mock_oauth_instance
            mock_oauth_instance.get_authorization_url.return_value = (
                "https://accounts.google.com/oauth2/auth?client_id=test",
                "test_state_123"
            )
            
            response = client.post("/api/v1/auth/google/login")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "auth_url" in data
            assert "state" in data
            assert data["success"] is True
            assert "accounts.google.com" in data["auth_url"]
    
    def test_google_callback_success(self, client, test_db_session, mock_google_oauth, mock_google_drive):
        """Test successful Google OAuth callback"""
        with patch('src.api.auth.GoogleOAuthService') as mock_oauth_class, \
             patch('src.api.auth.AuthService') as mock_auth_class, \
             patch('src.api.auth.GoogleDriveClient'):
            
            # Setup mocks
            mock_oauth_class.return_value = mock_google_oauth
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            
            # Mock user creation
            test_user = User(
                id=1,
                google_id="test_google_id_123",
                email="test@example.com",
                full_name="Test User",
                tier=UserTier.FREE
            )
            mock_auth_service.create_or_update_user_from_google.return_value = test_user
            mock_auth_service.create_user_tokens.return_value = ("access_token", "refresh_token")
            
            response = client.post("/api/v1/auth/google/callback", json={
                "code": "test_auth_code",
                "state": "test_state_123"
            })
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert "user" in data
            assert data["user"]["email"] == "test@example.com"
    
    def test_google_callback_invalid_state(self, client, mock_google_oauth):
        """Test Google OAuth callback with invalid state"""
        with patch('src.api.auth.GoogleOAuthService') as mock_oauth_class:
            mock_oauth_class.return_value = mock_google_oauth
            mock_google_oauth.verify_state.return_value = False
            
            response = client.post("/api/v1/auth/google/callback", json={
                "code": "test_auth_code",
                "state": "invalid_state"
            })
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Invalid state parameter" in data["detail"]
    
    def test_google_callback_invalid_code(self, client, mock_google_oauth):
        """Test Google OAuth callback with invalid authorization code"""
        with patch('src.api.auth.GoogleOAuthService') as mock_oauth_class:
            mock_oauth_class.return_value = mock_google_oauth
            mock_google_oauth.verify_state.return_value = True
            mock_google_oauth.exchange_code_for_tokens.return_value = None
            
            response = client.post("/api/v1/auth/google/callback", json={
                "code": "invalid_code",
                "state": "test_state_123"
            })
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.auth
class TestJWTTokens:
    """Test JWT token management"""
    
    def test_refresh_token_success(self, client, test_user):
        """Test successful token refresh"""
        with patch('src.api.auth.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.refresh_user_tokens.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token"
            }
            
            response = client.post("/api/v1/auth/refresh", json={
                "refresh_token": "valid_refresh_token"
            })
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["access_token"] == "new_access_token"
            assert data["refresh_token"] == "new_refresh_token"
            assert data["token_type"] == "bearer"
    
    def test_refresh_token_invalid(self, client):
        """Test token refresh with invalid refresh token"""
        with patch('src.api.auth.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.refresh_user_tokens.return_value = None
            
            response = client.post("/api/v1/auth/refresh", json={
                "refresh_token": "invalid_refresh_token"
            })
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_logout_success(self, client, auth_headers):
        """Test successful user logout"""
        with patch('src.api.auth.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = Mock(id=1)
            mock_auth_service.revoke_user_tokens.return_value = True
            
            response = client.post("/api/v1/auth/logout", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "Successfully logged out"
            assert data["success"] is True


@pytest.mark.auth  
class TestUserAuthentication:
    """Test user authentication and authorization"""
    
    def test_get_current_user_success(self, client, auth_headers, test_user):
        """Test getting current user information"""
        with patch('src.api.auth.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            mock_auth_service.get_user_statistics.return_value = {
                "documents": {"total": 5, "storage_used_bytes": 1024000},
                "categories": {"custom_categories": 3},
                "account": {"tier": "free", "google_drive_connected": False}
            }
            
            response = client.get("/api/v1/auth/me", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["email"] == test_user.email
            assert data["tier"] == test_user.tier.value
            assert "statistics" in data
    
    def test_get_current_user_unauthorized(self, client):
        """Test accessing protected endpoint without authentication"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_current_user_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        
        with patch('src.api.auth.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = None
            
            response = client.get("/api/v1/auth/me", headers=headers)
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.auth
@pytest.mark.google_drive
class TestGoogleDriveStatus:
    """Test Google Drive integration status"""
    
    def test_google_drive_status_connected(self, client, auth_headers, test_user, mock_google_drive):
        """Test Google Drive status when connected"""
        test_user.google_drive_connected = True
        test_user.google_drive_folder_id = "test_folder_id"
        
        with patch('src.api.auth.AuthService') as mock_auth_class, \
             patch('src.api.auth.GoogleDriveClient') as mock_drive_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_drive_class.return_value = mock_google_drive
            
            response = client.get("/api/v1/auth/google-drive/status", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["connected"] is True
            assert data["folder_id"] == "test_folder_id"
    
    def test_google_drive_reconnect(self, client, auth_headers, test_user, mock_google_oauth):
        """Test Google Drive reconnection flow"""
        with patch('src.api.auth.AuthService') as mock_auth_class, \
             patch('src.api.auth.GoogleOAuthService') as mock_oauth_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_oauth_class.return_value = mock_google_oauth
            
            response = client.post("/api/v1/auth/google-drive/reconnect", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "auth_url" in data
            assert "state" in data


@pytest.mark.unit
class TestAuthService:
    """Test AuthService business logic"""
    
    def test_create_user_tokens(self, test_db_session, test_user):
        """Test JWT token creation"""
        auth_service = AuthService(test_db_session)
        
        access_token, refresh_token = auth_service.create_user_tokens(test_user)
        
        assert access_token is not None
        assert refresh_token is not None
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
        assert len(access_token) > 50  # JWT tokens are long
        assert len(refresh_token) > 50
    
    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self, test_db_session, test_user):
        """Test getting current user with valid token"""
        auth_service = AuthService(test_db_session)
        
        # Create a token for the user
        access_token, _ = auth_service.create_user_tokens(test_user)
        
        # Get user from token
        retrieved_user = await auth_service.get_current_user(access_token)
        
        assert retrieved_user is not None
        assert retrieved_user.id == test_user.id
        assert retrieved_user.email == test_user.email
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, test_db_session):
        """Test getting current user with invalid token"""
        auth_service = AuthService(test_db_session)
        
        retrieved_user = await auth_service.get_current_user("invalid.jwt.token")
        
        assert retrieved_user is None
    
    @pytest.mark.asyncio
    async def test_create_or_update_user_from_google_new_user(self, test_db_session):
        """Test creating new user from Google OAuth data"""
        auth_service = AuthService(test_db_session)
        
        user = await auth_service.create_or_update_user_from_google(
            google_id="new_google_id_456",
            email="newuser@example.com",
            full_name="New User",
            avatar_url="https://example.com/avatar.jpg"
        )
        
        assert user is not None
        assert user.google_id == "new_google_id_456"
        assert user.email == "newuser@example.com"
        assert user.full_name == "New User"
        assert user.tier == UserTier.FREE
        assert user.is_active is True
        assert user.is_verified is True
    
    @pytest.mark.asyncio
    async def test_create_or_update_user_from_google_existing_user(self, test_db_session, test_user):
        """Test updating existing user from Google OAuth data"""
        auth_service = AuthService(test_db_session)
        
        # Update existing user
        updated_user = await auth_service.create_or_update_user_from_google(
            google_id=test_user.google_id,
            email="updated@example.com",
            full_name="Updated Name",
            avatar_url="https://example.com/new_avatar.jpg"
        )
        
        assert updated_user.id == test_user.id
        assert updated_user.email == "updated@example.com"
        assert updated_user.full_name == "Updated Name"
        assert updated_user.avatar_url == "https://example.com/new_avatar.jpg"