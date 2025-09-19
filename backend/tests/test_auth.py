# backend/tests/test_auth.py
"""
Bonifatus DMS - Authentication Tests
Core authentication tests for deployment verification
"""

import pytest
from unittest.mock import patch, Mock
from fastapi import status

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
    
    def test_google_callback_success(self, client, test_db_session, mock_google_oauth):
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


@pytest.mark.auth
class TestJWTTokens:
    """Test JWT token management"""
    
    def test_refresh_token_success(self, client, test_user):
        """Test successful token refresh"""
        with patch('src.api.auth.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.validate_refresh_token.return_value = test_user
            mock_auth_service.create_user_tokens.return_value = ("new_access_token", "new_refresh_token")
            
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
            mock_auth_service.validate_refresh_token.return_value = None
            
            response = client.post("/api/v1/auth/refresh", json={
                "refresh_token": "invalid_refresh_token"
            })
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED