"""
Unit tests for ProviderManager

Note: These tests verify the logic of ProviderManager methods.
Integration tests with real database should be performed separately.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from app.services.provider_manager import ProviderManager
from app.database.models import User, ProviderConnection


class TestProviderManager:
    """Test suite for ProviderManager"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return Mock()

    @pytest.fixture
    def mock_user(self):
        """Create a mock user"""
        user = Mock(spec=User)
        user.id = 'test-user-id'
        user.email = 'test@example.com'
        user.active_storage_provider = None
        return user

    @pytest.fixture
    def mock_connection(self):
        """Create a mock provider connection"""
        connection = Mock(spec=ProviderConnection)
        connection.id = 'test-connection-id'
        connection.user_id = 'test-user-id'
        connection.provider_key = 'google_drive'
        connection.refresh_token_encrypted = 'encrypted_token_123'
        connection.access_token_encrypted = None
        connection.is_enabled = True
        connection.is_active = True
        connection.connected_at = datetime.utcnow()
        connection.last_used_at = None
        connection.metadata_json = None
        return connection

    def test_get_connection_success(self, mock_db, mock_user, mock_connection):
        """Test getting an existing provider connection"""
        # Setup mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_connection
        mock_db.query.return_value = mock_query

        # Execute
        result = ProviderManager.get_connection(mock_db, mock_user, 'google_drive')

        # Verify
        assert result == mock_connection
        mock_db.query.assert_called_once_with(ProviderConnection)

    def test_get_connection_not_found(self, mock_db, mock_user):
        """Test getting a non-existent provider connection"""
        # Setup mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Execute
        result = ProviderManager.get_connection(mock_db, mock_user, 'nonexistent')

        # Verify
        assert result is None

    def test_get_token_success(self, mock_db, mock_user, mock_connection):
        """Test getting encrypted token for connected provider"""
        # Setup
        with patch.object(ProviderManager, 'get_connection', return_value=mock_connection):
            # Execute
            token = ProviderManager.get_token(mock_db, mock_user, 'google_drive')

            # Verify
            assert token == 'encrypted_token_123'

    def test_get_token_provider_not_connected(self, mock_db, mock_user):
        """Test getting token when provider is not connected"""
        # Setup
        with patch.object(ProviderManager, 'get_connection', return_value=None):
            # Execute
            token = ProviderManager.get_token(mock_db, mock_user, 'google_drive')

            # Verify
            assert token is None

    def test_is_enabled_true(self, mock_db, mock_user, mock_connection):
        """Test is_enabled returns True for enabled provider"""
        # Setup
        with patch.object(ProviderManager, 'get_connection', return_value=mock_connection):
            # Execute
            result = ProviderManager.is_enabled(mock_db, mock_user, 'google_drive')

            # Verify
            assert result is True

    def test_is_enabled_false(self, mock_db, mock_user, mock_connection):
        """Test is_enabled returns False for disabled provider"""
        # Setup
        mock_connection.is_enabled = False
        with patch.object(ProviderManager, 'get_connection', return_value=mock_connection):
            # Execute
            result = ProviderManager.is_enabled(mock_db, mock_user, 'google_drive')

            # Verify
            assert result is False

    def test_is_enabled_not_connected(self, mock_db, mock_user):
        """Test is_enabled returns False when provider not connected"""
        # Setup
        with patch.object(ProviderManager, 'get_connection', return_value=None):
            # Execute
            result = ProviderManager.is_enabled(mock_db, mock_user, 'google_drive')

            # Verify
            assert result is False

    def test_is_connected_true(self, mock_db, mock_user, mock_connection):
        """Test is_connected returns True when provider is enabled and has token"""
        # Setup
        with patch.object(ProviderManager, 'get_connection', return_value=mock_connection):
            # Execute
            result = ProviderManager.is_connected(mock_db, mock_user, 'google_drive')

            # Verify
            assert result is True

    def test_is_connected_false_no_token(self, mock_db, mock_user, mock_connection):
        """Test is_connected returns False when provider has no token"""
        # Setup
        mock_connection.refresh_token_encrypted = None
        with patch.object(ProviderManager, 'get_connection', return_value=mock_connection):
            # Execute
            result = ProviderManager.is_connected(mock_db, mock_user, 'google_drive')

            # Verify
            assert result is False

    def test_is_connected_false_disabled(self, mock_db, mock_user, mock_connection):
        """Test is_connected returns False when provider is disabled"""
        # Setup
        mock_connection.is_enabled = False
        with patch.object(ProviderManager, 'get_connection', return_value=mock_connection):
            # Execute
            result = ProviderManager.is_connected(mock_db, mock_user, 'google_drive')

            # Verify
            assert result is False

    def test_get_enabled_providers(self, mock_db, mock_user):
        """Test getting list of enabled provider keys"""
        # Setup mock connections
        gd_conn = Mock(provider_key='google_drive')
        od_conn = Mock(provider_key='onedrive')

        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [gd_conn, od_conn]
        mock_db.query.return_value = mock_query

        # Execute
        result = ProviderManager.get_enabled_providers(mock_db, mock_user)

        # Verify
        assert result == ['google_drive', 'onedrive']

    def test_get_other_enabled_provider_success(self, mock_db, mock_user):
        """Test getting another enabled provider"""
        # Setup mock connection
        od_conn = Mock(provider_key='onedrive')

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = od_conn
        mock_db.query.return_value = mock_query

        # Execute
        result = ProviderManager.get_other_enabled_provider(mock_db, mock_user, 'google_drive')

        # Verify
        assert result == 'onedrive'

    def test_get_other_enabled_provider_none_found(self, mock_db, mock_user):
        """Test getting other provider when none exists"""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Execute
        result = ProviderManager.get_other_enabled_provider(mock_db, mock_user, 'google_drive')

        # Verify
        assert result is None

    @patch('app.core.provider_registry.ProviderRegistry.exists')
    def test_connect_provider_validates_provider_exists(self, mock_exists, mock_db, mock_user):
        """Test connect_provider validates provider exists in registry"""
        # Setup
        mock_exists.return_value = False

        # Execute & Verify
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderManager.connect_provider(
                mock_db,
                mock_user,
                'invalid_provider',
                'token123'
            )

    def test_get_connection_info_success(self, mock_db, mock_user, mock_connection):
        """Test getting connection info for API responses"""
        # Setup
        with patch.object(ProviderManager, 'get_connection', return_value=mock_connection):
            with patch('app.services.provider_manager.ProviderRegistry.get') as mock_get:
                mock_metadata = Mock()
                mock_metadata.display_name = 'Google Drive'
                mock_get.return_value = mock_metadata

                # Execute
                result = ProviderManager.get_connection_info(mock_db, mock_user, 'google_drive')

                # Verify
                assert result is not None
                assert result['provider_key'] == 'google_drive'
                assert result['display_name'] == 'Google Drive'
                assert result['is_enabled'] is True
                assert result['is_active'] is True

    def test_get_connection_info_not_connected(self, mock_db, mock_user):
        """Test getting connection info when provider not connected"""
        # Setup
        with patch.object(ProviderManager, 'get_connection', return_value=None):
            # Execute
            result = ProviderManager.get_connection_info(mock_db, mock_user, 'google_drive')

            # Verify
            assert result is None
