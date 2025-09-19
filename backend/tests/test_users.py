# backend/tests/test_users.py
"""
Bonifatus DMS - User Tests
Core user management tests for deployment verification
"""

import pytest
from unittest.mock import patch, Mock
from fastapi import status

from src.database.models import User, UserTier


@pytest.mark.integration
class TestUserAPI:
    """Test user management API endpoints"""

    def test_get_user_profile_success(self, client, auth_headers, test_user):
        """Test getting user profile information"""
        with patch("src.api.users.AuthService") as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user

            response = client.get("/api/v1/users/profile", headers=auth_headers)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == test_user.id
            assert data["email"] == test_user.email
            assert data["full_name"] == test_user.full_name
            assert data["tier"] == test_user.tier.value
            assert "created_at" in data
