# backend/tests/test_users.py
"""
Bonifatus DMS - User Tests
Comprehensive tests for user management, settings, and statistics
"""

import pytest
from unittest.mock import patch, Mock
from fastapi import status
from datetime import datetime, timedelta

from src.database.models import User, UserSettings, UserTier
from src.services.user_service import UserService


@pytest.mark.integration
class TestUserAPI:
    """Test user management API endpoints"""
    
    def test_get_user_profile_success(self, client, auth_headers, test_user):
        """Test getting user profile"""
        with patch('src.api.users.AuthService') as mock_auth_class, \
             patch('src.api.users.UserService') as mock_user_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_user_service = Mock()
            mock_user_class.return_value = mock_user_service
            mock_user_service.get_complete_profile.return_value = {
                "tier_limits": {
                    "document_limit": 100,
                    "monthly_uploads": 50
                },
                "trial_info": {
                    "has_used_trial": False,
                    "trial_available": True
                },
                "statistics": {
                    "documents": {"total": 5},
                    "categories": {"custom_categories": 2}
                }
            }
            
            response = client.get("/api/v1/users/profile", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "user" in data
            assert "usage" in data
            assert "google_drive" in data
            assert data["user"]["email"] == test_user.email
    
    def test_update_user_profile_success(self, client, auth_headers, test_user):
        """Test updating user profile"""
        update_data = {
            "full_name": "Updated Name",
            "preferred_language": "de",
            "theme": "dark"
        }
        
        with patch('src.api.users.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            with patch('src.api.users.db.commit'):
                response = client.put(
                    "/api/v1/users/profile",
                    params=update_data,
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["success"] is True
    
    def test_get_user_settings_success(self, client, auth_headers, test_user):
        """Test getting user settings"""
        with patch('src.api.users.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            # Mock user settings
            mock_settings = UserSettings(
                user_id=test_user.id,
                auto_categorization_enabled=True,
                ocr_enabled=True,
                documents_per_page=20
            )
            
            with patch('src.api.users.db.query') as mock_query:
                mock_query.return_value.filter.return_value.first.return_value = mock_settings
                
                response = client.get("/api/v1/users/settings", headers=auth_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "document_processing" in data
                assert "notifications" in data
                assert "google_drive" in data
                assert "ui_preferences" in data
    
    def test_update_user_settings_success(self, client, auth_headers, test_user):
        """Test updating user settings"""
        settings_data = {
            "document_processing": {
                "auto_categorization_enabled": False,
                "ocr_enabled": True
            },
            "ui_preferences": {
                "documents_per_page": 50,
                "default_view_mode": "list"
            }
        }
        
        with patch('src.api.users.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_settings = UserSettings(user_id=test_user.id)
            
            with patch('src.api.users.db.query') as mock_query, \
                 patch('src.api.users.db.commit'):
                mock_query.return_value.filter.return_value.first.return_value = mock_settings
                
                response = client.put(
                    "/api/v1/users/settings",
                    json=settings_data,
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["success"] is True
    
    def test_get_user_statistics_success(self, client, auth_headers, test_user):
        """Test getting user statistics"""
        with patch('src.api.users.AuthService') as mock_auth_class, \
             patch('src.api.users.UserService') as mock_user_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_user_service = Mock()
            mock_user_class.return_value = mock_user_service
            mock_user_service.get_usage_statistics.return_value = {
                "period": "month",
                "documents": {
                    "total": 10,
                    "period_uploads": 3,
                    "storage_bytes": 1048576
                },
                "categories": [
                    {"name": "Finance", "document_count": 5},
                    {"name": "Personal", "document_count": 5}
                ]
            }
            
            response = client.get("/api/v1/users/statistics?period=month", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "statistics" in data
            assert data["period"] == "month"
    
    def test_start_premium_trial_success(self, client, auth_headers, test_user):
        """Test starting premium trial"""
        test_user.tier = UserTier.FREE
        test_user.trial_started_at = None
        
        with patch('src.api.users.AuthService') as mock_auth_class, \
             patch('src.api.users.UserService') as mock_user_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_user_service = Mock()
            mock_user_class.return_value = mock_user_service
            mock_user_service.start_premium_trial.return_value = {
                "success": True,
                "trial_ends_at": (datetime.utcnow() + timedelta(days=30)).isoformat()
            }
            
            response = client.post("/api/v1/users/upgrade-trial", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "trial_ends_at" in data
    
    def test_start_premium_trial_already_used(self, client, auth_headers, test_user):
        """Test starting trial when already used"""
        test_user.tier = UserTier.FREE
        test_user.trial_started_at = datetime.utcnow() - timedelta(days=60)
        
        with patch('src.api.users.AuthService') as mock_auth_class:
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            response = client.post("/api/v1/users/upgrade-trial", headers=auth_headers)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "already used" in response.json()["detail"]
    
    def test_export_user_data_success(self, client, auth_headers, test_user):
        """Test exporting user data"""
        with patch('src.api.users.AuthService') as mock_auth_class, \
             patch('src.api.users.UserService') as mock_user_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_user_service = Mock()
            mock_user_class.return_value = mock_user_service
            mock_user_service.export_user_data.return_value = {
                "profile": {"email": test_user.email},
                "documents": [],
                "categories": []
            }
            
            response = client.get("/api/v1/users/export-data?format=json", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "data" in data
            assert data["gdpr_compliant"] is True
    
    def test_delete_user_account_success(self, client, auth_headers, test_user):
        """Test deleting user account"""
        confirmation = f"DELETE {test_user.email}"
        
        with patch('src.api.users.AuthService') as mock_auth_class, \
             patch('src.api.users.UserService') as mock_user_class:
            
            mock_auth_service = Mock()
            mock_auth_class.return_value = mock_auth_service
            mock_auth_service.get_current_user.return_value = test_user
            
            mock_user_service = Mock()
            mock_user_class.return_value = mock_user_service
            mock_user_service.delete_user_account.return_value = {
                "success": True,
                "deleted_documents": 5,
                "deleted_categories": 2,
                "google_drive_files_deleted": 0
            }
            
            response = client.delete(
                f"/api/v1/users/account?confirmation={confirmation}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True


@pytest.mark.unit
class TestUserService:
    """Test UserService business logic"""
    
    @pytest.mark.asyncio
    async def test_get_complete_profile(self, test_db_session, test_user):
        """Test getting complete user profile"""
        user_service = UserService(test_db_session)
        
        profile = await user_service.get_complete_profile(test_user.id)
        
        assert isinstance(profile, dict)
        assert "tier_limits" in profile
        assert "trial_info" in profile
        assert "statistics" in profile
    
    @pytest.mark.asyncio
    async def test_get_usage_statistics(self, test_db_session, test_user):
        """Test getting usage statistics"""
        user_service = UserService(test_db_session)
        
        stats = await user_service.get_usage_statistics(test_user.id, "month")
        
        assert isinstance(stats, dict)
        assert "period" in stats
        assert "documents" in stats
        assert "categories" in stats
        assert stats["period"] == "month"
    
    @pytest.mark.asyncio
    async def test_start_premium_trial_success(self, test_db_session, test_user):
        """Test starting premium trial"""
        user_service = UserService(test_db_session)
        
        # Ensure user is eligible
        test_user.tier = UserTier.FREE
        test_user.trial_started_at = None
        test_db_session.add(test_user)
        test_db_session.commit()
        
        result = await user_service.start_premium_trial(test_user.id)
        
        assert result["success"] is True
        assert "trial_ends_at" in result
        
        # Check user was updated
        updated_user = test_db_session.query(User).filter(User.id == test_user.id).first()
        assert updated_user.tier == UserTier.PREMIUM_TRIAL
        assert updated_user.trial_started_at is not None
    
    @pytest.mark.asyncio
    async def test_start_premium_trial_ineligible(self, test_db_session, test_user):
        """Test starting trial when ineligible"""
        user_service = UserService(test_db_session)
        
        # User already premium
        test_user.tier = UserTier.PREMIUM
        test_db_session.add(test_user)
        test_db_session.commit()
        
        result = await user_service.start_premium_trial(test_user.id)
        
        assert result["success"] is False
        assert "only available for free users" in result["error"]
    
    @pytest.mark.asyncio
    async def test_export_user_data(self, test_db_session, test_user):
        """Test exporting user data"""
        user_service = UserService(test_db_session)
        
        export_data = await user_service.export_user_data(test_user.id, "json")
        
        assert isinstance(export_data, dict)
        assert "profile" in export_data
        assert "documents" in export_data
        assert "categories" in export_data
        assert export_data["profile"]["email"] == test_user.email
    
    @pytest.mark.asyncio
    async def test_delete_user_account(self, test_db_session, test_user):
        """Test deleting user account"""
        user_service = UserService(test_db_session)
        
        # Add user to session
        test_db_session.add(test_user)
        test_db_session.commit()
        user_id = test_user.id
        
        result = await user_service.delete_user_account(user_id, False)
        
        assert result["success"] is True
        assert "deleted_documents" in result
        assert "deleted_categories" in result
        
        # Verify user is deleted
        deleted_user = test_db_session.query(User).filter(User.id == user_id).first()
        assert deleted_user is None
    
    def test_get_tier_limits(self, test_db_session):
        """Test getting tier limits"""
        user_service = UserService(test_db_session)
        
        free_limits = user_service._get_tier_limits(UserTier.FREE)
        premium_limits = user_service._get_tier_limits(UserTier.PREMIUM)
        
        assert free_limits["document_limit"] == 100
        assert premium_limits["document_limit"] == 0  # Unlimited
        assert free_limits["monthly_uploads"] < premium_limits["monthly_uploads"] or premium_limits["monthly_uploads"] == 0
    
    def test_get_trial_info_no_trial(self, test_db_session, test_user):
        """Test getting trial info for user who hasn't used trial"""
        user_service = UserService(test_db_session)
        
        test_user.trial_started_at = None
        test_user.tier = UserTier.FREE
        
        trial_info = user_service._get_trial_info(test_user)
        
        assert trial_info["has_used_trial"] is False
        assert trial_info["trial_available"] is True
    
    def test_get_trial_info_active_trial(self, test_db_session, test_user):
        """Test getting trial info for user with active trial"""
        user_service = UserService(test_db_session)
        
        test_user.trial_started_at = datetime.utcnow() - timedelta(days=5)
        test_user.trial_ended_at = datetime.utcnow() + timedelta(days=25)
        test_user.tier = UserTier.PREMIUM_TRIAL
        
        trial_info = user_service._get_trial_info(test_user)
        
        assert trial_info["has_used_trial"] is True
        assert trial_info["trial_active"] is True
        assert trial_info["days_remaining"] == 25