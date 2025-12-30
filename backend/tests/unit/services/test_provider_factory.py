"""
Unit tests for ProviderFactory
"""
import pytest
from app.services.storage.provider_factory import ProviderFactory
from app.services.storage.base_provider import StorageProvider


class TestProviderFactory:
    """Test suite for ProviderFactory"""

    def test_create_google_drive_provider(self):
        """Test creating Google Drive provider instance"""
        provider = ProviderFactory.create('google_drive')

        assert provider is not None
        assert isinstance(provider, StorageProvider)

    def test_create_onedrive_provider(self):
        """Test creating OneDrive provider instance"""
        provider = ProviderFactory.create('onedrive')

        assert provider is not None
        assert isinstance(provider, StorageProvider)

    def test_create_invalid_provider_raises_error(self):
        """Test creating provider with invalid key raises ValueError"""
        with pytest.raises(ValueError, match="Unknown storage provider"):
            ProviderFactory.create('nonexistent_provider')

    def test_get_available_providers_includes_active_providers(self):
        """Test getting list of available providers"""
        providers = ProviderFactory.get_available_providers()

        # Should include at least Google Drive and OneDrive
        assert 'google_drive' in providers
        assert 'onedrive' in providers
        assert isinstance(providers, list)

    def test_is_provider_available_true(self):
        """Test is_provider_available returns True for registered providers"""
        assert ProviderFactory.is_provider_available('google_drive') is True
        assert ProviderFactory.is_provider_available('onedrive') is True

    def test_is_provider_available_false(self):
        """Test is_provider_available returns False for unregistered providers"""
        assert ProviderFactory.is_provider_available('nonexistent') is False

    def test_factory_auto_registers_providers_from_registry(self):
        """Test that factory automatically registers providers from registry on module import"""
        # This test verifies that _register_available_providers() ran successfully
        # by checking that providers from the registry are available in the factory

        available = ProviderFactory.get_available_providers()

        # Google Drive and OneDrive are active in the registry
        assert 'google_drive' in available
        assert 'onedrive' in available

        # Dropbox and Box are inactive, so they may or may not be available
        # (depending on whether their implementation classes exist)

    def test_created_providers_are_independent_instances(self):
        """Test that each call to create() returns a new instance"""
        provider1 = ProviderFactory.create('google_drive')
        provider2 = ProviderFactory.create('google_drive')

        # Should be different instances
        assert provider1 is not provider2

    def test_providers_implement_storage_provider_interface(self):
        """Test that created providers implement required StorageProvider methods"""
        provider = ProviderFactory.create('google_drive')

        # Check for required methods from StorageProvider base class
        assert hasattr(provider, 'upload_file')
        assert hasattr(provider, 'download_file')
        assert hasattr(provider, 'delete_file')
        assert hasattr(provider, 'get_authorization_url')
        assert hasattr(provider, 'exchange_code_for_token')
        assert callable(getattr(provider, 'upload_file'))
        assert callable(getattr(provider, 'download_file'))
        assert callable(getattr(provider, 'delete_file'))
