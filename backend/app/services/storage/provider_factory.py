"""
Provider factory for creating storage provider instances.

This factory pattern allows for easy addition of new storage providers
without modifying core application logic.
"""

from typing import Type, Dict
from app.services.storage.base_provider import StorageProvider


class ProviderFactory:
    """
    Factory class for creating storage provider instances.

    This factory uses a registry pattern to dynamically create provider instances
    based on the provider type string. New providers can be added by importing
    the provider class and adding it to the _providers dictionary.

    Example:
        provider = ProviderFactory.create('google_drive')
        auth_url = provider.get_authorization_url(state='user_123', redirect_uri='https://...')
    """

    _providers: Dict[str, Type[StorageProvider]] = {}

    @classmethod
    def register_provider(cls, provider_type: str, provider_class: Type[StorageProvider]) -> None:
        """
        Register a new storage provider.

        Args:
            provider_type: Unique identifier for the provider (e.g., 'google_drive')
            provider_class: Class that implements StorageProvider interface

        Raises:
            ValueError: If provider_type is already registered
        """
        if provider_type in cls._providers:
            raise ValueError(f"Provider '{provider_type}' is already registered")
        cls._providers[provider_type] = provider_class

    @classmethod
    def create(cls, provider_type: str) -> StorageProvider:
        """
        Create a storage provider instance.

        Args:
            provider_type: Provider identifier (e.g., 'google_drive', 'onedrive')

        Returns:
            Instantiated storage provider

        Raises:
            ValueError: If provider_type is not registered

        Example:
            provider = ProviderFactory.create('onedrive')
        """
        provider_class = cls._providers.get(provider_type)
        if not provider_class:
            available = ', '.join(cls._providers.keys()) if cls._providers else 'none'
            raise ValueError(
                f"Unknown storage provider: '{provider_type}'. "
                f"Available providers: {available}"
            )
        return provider_class()

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """
        Get list of all registered provider types.

        Returns:
            List of provider type identifiers

        Example:
            providers = ProviderFactory.get_available_providers()
            # Returns: ['google_drive', 'onedrive']
        """
        return list(cls._providers.keys())

    @classmethod
    def is_provider_available(cls, provider_type: str) -> bool:
        """
        Check if a provider type is registered.

        Args:
            provider_type: Provider identifier to check

        Returns:
            True if provider is registered, False otherwise
        """
        return provider_type in cls._providers


# Auto-registration of available providers
# Providers are imported and registered here to avoid circular imports
def _register_available_providers():
    """
    Register all available storage providers.

    This function is called automatically when the module is imported.
    As new providers are implemented, add their imports and registration here.
    """
    try:
        from app.services.storage.google_drive_provider import GoogleDriveProvider
        ProviderFactory.register_provider('google_drive', GoogleDriveProvider)
    except ImportError:
        # Google Drive provider not yet implemented
        pass

    try:
        from app.services.storage.onedrive_provider import OneDriveProvider
        ProviderFactory.register_provider('onedrive', OneDriveProvider)
    except ImportError:
        # OneDrive provider not yet implemented
        pass

    try:
        from app.services.storage.dropbox_provider import DropboxProvider
        ProviderFactory.register_provider('dropbox', DropboxProvider)
    except ImportError:
        # Dropbox provider not yet implemented (future)
        pass

    try:
        from app.services.storage.box_provider import BoxProvider
        ProviderFactory.register_provider('box', BoxProvider)
    except ImportError:
        # Box provider not yet implemented (future)
        pass


# Register providers on module import
_register_available_providers()
