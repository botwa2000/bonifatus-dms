"""
Provider factory for creating storage provider instances.

This factory pattern allows for easy addition of new storage providers
without modifying core application logic. Providers are automatically
loaded from the ProviderRegistry using dynamic imports.
"""

from typing import Type, Dict
import importlib
from app.services.storage.base_provider import StorageProvider
from app.core.provider_registry import ProviderRegistry


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


# Auto-registration of available providers from registry
def _register_available_providers():
    """
    Register all available storage providers from ProviderRegistry.

    This function dynamically loads provider classes using importlib based on
    the provider_class_path stored in the ProviderRegistry. New providers are
    automatically registered when added to the registry - no code changes needed here.

    Example registry entry:
        ProviderRegistry.register(ProviderMetadata(
            provider_key='google_drive',
            provider_class_path='app.services.storage.google_drive_provider.GoogleDriveProvider',
            ...
        ))
    """
    # Get all active providers from the registry
    for provider_metadata in ProviderRegistry.get_active():
        try:
            # Parse the class path (e.g., 'app.services.storage.google_drive_provider.GoogleDriveProvider')
            module_path, class_name = provider_metadata.provider_class_path.rsplit('.', 1)

            # Dynamically import the module
            module = importlib.import_module(module_path)

            # Get the class from the module
            provider_class = getattr(module, class_name)

            # Register the provider
            ProviderFactory.register_provider(provider_metadata.provider_key, provider_class)

        except (ImportError, AttributeError) as e:
            # Provider class not yet implemented or import error
            # This is expected for future providers (Dropbox, Box)
            pass


# Register providers on module import
_register_available_providers()
