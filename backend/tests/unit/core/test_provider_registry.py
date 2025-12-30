"""
Unit tests for ProviderRegistry
"""
import pytest
from app.core.provider_registry import ProviderRegistry
from app.core.provider_config import ProviderMetadata, ProviderCapability


class TestProviderRegistry:
    """Test suite for ProviderRegistry"""

    def test_get_google_drive_provider(self):
        """Test getting Google Drive provider metadata"""
        metadata = ProviderRegistry.get('google_drive')

        assert metadata is not None
        assert metadata.provider_key == 'google_drive'
        assert metadata.display_name == 'Google Drive'
        assert metadata.is_active is True
        assert ProviderCapability.FILE_UPLOAD in metadata.capabilities

    def test_get_onedrive_provider(self):
        """Test getting OneDrive provider metadata"""
        metadata = ProviderRegistry.get('onedrive')

        assert metadata is not None
        assert metadata.provider_key == 'onedrive'
        assert metadata.display_name == 'OneDrive'
        assert metadata.is_active is True

    def test_get_nonexistent_provider(self):
        """Test getting provider that doesn't exist"""
        metadata = ProviderRegistry.get('nonexistent')
        assert metadata is None

    def test_exists_for_registered_provider(self):
        """Test exists() returns True for registered providers"""
        assert ProviderRegistry.exists('google_drive') is True
        assert ProviderRegistry.exists('onedrive') is True

    def test_exists_for_unregistered_provider(self):
        """Test exists() returns False for unregistered providers"""
        assert ProviderRegistry.exists('nonexistent') is False

    def test_get_all_providers(self):
        """Test getting all providers"""
        providers = ProviderRegistry.get_all()

        assert len(providers) >= 2  # At least Google Drive and OneDrive
        assert all(isinstance(p, ProviderMetadata) for p in providers)

        # Check providers are sorted by sort_order
        sort_orders = [p.sort_order for p in providers]
        assert sort_orders == sorted(sort_orders)

    def test_get_active_providers(self):
        """Test getting only active providers"""
        active_providers = ProviderRegistry.get_active()

        # Google Drive and OneDrive should be active
        active_keys = [p.provider_key for p in active_providers]
        assert 'google_drive' in active_keys
        assert 'onedrive' in active_keys

        # All returned providers should have is_active=True
        assert all(p.is_active for p in active_providers)

    def test_get_by_capability_file_upload(self):
        """Test filtering providers by FILE_UPLOAD capability"""
        providers = ProviderRegistry.get_by_capability(ProviderCapability.FILE_UPLOAD)

        assert len(providers) >= 2
        assert all(ProviderCapability.FILE_UPLOAD in p.capabilities for p in providers)

    def test_get_by_capability_folder_deletion(self):
        """Test filtering providers by FOLDER_DELETION capability"""
        providers = ProviderRegistry.get_by_capability(ProviderCapability.FOLDER_DELETION)

        # Google Drive should support folder deletion
        provider_keys = [p.provider_key for p in providers]
        assert 'google_drive' in provider_keys

    def test_get_display_name_for_registered_provider(self):
        """Test getting display name for registered provider"""
        display_name = ProviderRegistry.get_display_name('google_drive')
        assert display_name == 'Google Drive'

    def test_get_display_name_for_unregistered_provider(self):
        """Test getting display name for unregistered provider falls back to formatted key"""
        display_name = ProviderRegistry.get_display_name('my_custom_provider')
        assert display_name == 'My Custom Provider'  # Formatted from key

    def test_provider_metadata_has_required_fields(self):
        """Test that provider metadata has all required fields"""
        metadata = ProviderRegistry.get('google_drive')

        # Identity
        assert hasattr(metadata, 'provider_key')
        assert hasattr(metadata, 'display_name')

        # OAuth
        assert hasattr(metadata, 'oauth_client_id_secret')
        assert hasattr(metadata, 'oauth_client_secret_secret')
        assert hasattr(metadata, 'oauth_scopes')
        assert hasattr(metadata, 'oauth_redirect_uri_env')

        # Storage
        assert hasattr(metadata, 'folder_name_env')
        assert hasattr(metadata, 'default_folder_name')

        # Provider Class
        assert hasattr(metadata, 'provider_class_path')

        # UI
        assert hasattr(metadata, 'icon')
        assert hasattr(metadata, 'description')

        # Features
        assert hasattr(metadata, 'capabilities')
        assert hasattr(metadata, 'min_tier_id')
        assert hasattr(metadata, 'is_active')

    def test_provider_class_path_format(self):
        """Test that provider class paths are properly formatted"""
        metadata = ProviderRegistry.get('google_drive')

        # Should be in format: module.path.ClassName
        assert '.' in metadata.provider_class_path
        assert metadata.provider_class_path.startswith('app.services.storage.')

        # Should end with class name
        assert metadata.provider_class_path.endswith('Provider')
