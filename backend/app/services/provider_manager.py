"""
Provider Manager - Centralized database operations for storage providers.

This service provides a unified interface for managing provider connections,
replacing all direct database field access (user.google_drive_enabled, etc.)
with dynamic, provider-agnostic operations.

Design: All provider operations go through this manager, which uses
ProviderRegistry for metadata and the provider_connections table for storage.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database.models import User, ProviderConnection
from app.core.provider_registry import ProviderRegistry


class ProviderManager:
    """
    Centralized manager for storage provider operations.

    This class eliminates 60+ instances of direct field access throughout
    the codebase (e.g., user.google_drive_enabled, user.onedrive_refresh_token_encrypted).

    All provider operations should use this manager instead of accessing
    database fields directly or using hardcoded if/elif chains.
    """

    @staticmethod
    def get_connection(
        db: Session,
        user: User,
        provider_key: str
    ) -> Optional[ProviderConnection]:
        """
        Get provider connection for a user.

        Args:
            db: Database session
            user: User instance
            provider_key: Provider identifier

        Returns:
            ProviderConnection or None if not connected
        """
        return db.query(ProviderConnection).filter(
            and_(
                ProviderConnection.user_id == user.id,
                ProviderConnection.provider_key == provider_key
            )
        ).first()

    @staticmethod
    def get_token(
        db: Session,
        user: User,
        provider_key: str
    ) -> Optional[str]:
        """
        Get encrypted refresh token for a provider.

        Args:
            db: Database session
            user: User instance
            provider_key: Provider identifier

        Returns:
            Encrypted refresh token or None if not connected
        """
        connection = ProviderManager.get_connection(db, user, provider_key)
        return connection.refresh_token_encrypted if connection else None

    @staticmethod
    def is_enabled(
        db: Session,
        user: User,
        provider_key: str
    ) -> bool:
        """
        Check if provider is enabled for user.

        Args:
            db: Database session
            user: User instance
            provider_key: Provider identifier

        Returns:
            True if provider is enabled, False otherwise
        """
        connection = ProviderManager.get_connection(db, user, provider_key)
        return connection.is_enabled if connection else False

    @staticmethod
    def is_connected(
        db: Session,
        user: User,
        provider_key: str
    ) -> bool:
        """
        Check if provider is connected (has token and is enabled).

        Args:
            db: Database session
            user: User instance
            provider_key: Provider identifier

        Returns:
            True if provider is connected, False otherwise
        """
        connection = ProviderManager.get_connection(db, user, provider_key)
        if not connection:
            return False
        return connection.is_enabled and bool(connection.refresh_token_encrypted)

    @staticmethod
    def connect_provider(
        db: Session,
        user: User,
        provider_key: str,
        refresh_token_encrypted: str,
        access_token_encrypted: Optional[str] = None,
        set_as_active: bool = True
    ) -> ProviderConnection:
        """
        Connect a storage provider for a user.

        Creates or updates a provider connection with the given credentials.

        Args:
            db: Database session
            user: User instance
            provider_key: Provider identifier
            refresh_token_encrypted: Encrypted refresh token
            access_token_encrypted: Optional encrypted access token
            set_as_active: Whether to set this as the active provider

        Returns:
            Created or updated ProviderConnection

        Raises:
            ValueError: If provider_key is not registered
        """
        # Validate provider exists
        if not ProviderRegistry.exists(provider_key):
            raise ValueError(f"Unknown provider: {provider_key}")

        # Check if connection already exists
        connection = ProviderManager.get_connection(db, user, provider_key)

        if connection:
            # Update existing connection
            connection.refresh_token_encrypted = refresh_token_encrypted
            connection.access_token_encrypted = access_token_encrypted
            connection.is_enabled = True
            connection.connected_at = datetime.utcnow()
        else:
            # Create new connection
            connection = ProviderConnection(
                user_id=user.id,
                provider_key=provider_key,
                refresh_token_encrypted=refresh_token_encrypted,
                access_token_encrypted=access_token_encrypted,
                is_enabled=True,
                is_active=False,
                connected_at=datetime.utcnow()
            )
            db.add(connection)

        # Set as active if requested
        if set_as_active:
            ProviderManager._set_active_internal(db, user, provider_key)

        db.commit()
        db.refresh(connection)
        return connection

    @staticmethod
    def disconnect_provider(
        db: Session,
        user: User,
        provider_key: str
    ) -> bool:
        """
        Disconnect a storage provider for a user.

        Removes the provider connection and all associated credentials.

        Args:
            db: Database session
            user: User instance
            provider_key: Provider identifier

        Returns:
            True if connection was removed, False if it didn't exist
        """
        connection = ProviderManager.get_connection(db, user, provider_key)
        if not connection:
            return False

        # If this was the active provider, clear active status
        if connection.is_active:
            user.active_storage_provider = None

        # Delete the connection
        db.delete(connection)
        db.commit()
        return True

    @staticmethod
    def get_enabled_providers(
        db: Session,
        user: User
    ) -> List[str]:
        """
        Get list of enabled provider keys for a user.

        Args:
            db: Database session
            user: User instance

        Returns:
            List of enabled provider keys
        """
        connections = db.query(ProviderConnection).filter(
            and_(
                ProviderConnection.user_id == user.id,
                ProviderConnection.is_enabled == True
            )
        ).all()

        return [conn.provider_key for conn in connections]

    @staticmethod
    def get_active_provider(
        db: Session,
        user: User
    ) -> Optional[ProviderConnection]:
        """
        Get the active provider connection for a user.

        Args:
            db: Database session
            user: User instance

        Returns:
            Active ProviderConnection or None
        """
        return db.query(ProviderConnection).filter(
            and_(
                ProviderConnection.user_id == user.id,
                ProviderConnection.is_active == True
            )
        ).first()

    @staticmethod
    def set_active_provider(
        db: Session,
        user: User,
        provider_key: str
    ) -> None:
        """
        Set a provider as the active storage provider for a user.

        Args:
            db: Database session
            user: User instance
            provider_key: Provider identifier

        Raises:
            ValueError: If provider is not connected or doesn't exist
        """
        # Verify provider is connected
        connection = ProviderManager.get_connection(db, user, provider_key)
        if not connection or not connection.is_enabled:
            raise ValueError(f"Provider {provider_key} is not connected")

        ProviderManager._set_active_internal(db, user, provider_key)
        db.commit()

    @staticmethod
    def _set_active_internal(
        db: Session,
        user: User,
        provider_key: str
    ) -> None:
        """
        Internal method to set active provider (doesn't commit).

        Args:
            db: Database session
            user: User instance
            provider_key: Provider to set as active
        """
        # Deactivate all current connections
        db.query(ProviderConnection).filter(
            ProviderConnection.user_id == user.id
        ).update({ProviderConnection.is_active: False})

        # Activate the specified provider
        db.query(ProviderConnection).filter(
            and_(
                ProviderConnection.user_id == user.id,
                ProviderConnection.provider_key == provider_key
            )
        ).update({ProviderConnection.is_active: True})

        # Update User table for backward compatibility
        user.active_storage_provider = provider_key

    @staticmethod
    def update_last_used(
        db: Session,
        user: User,
        provider_key: str
    ) -> None:
        """
        Update the last_used_at timestamp for a provider.

        Args:
            db: Database session
            user: User instance
            provider_key: Provider identifier
        """
        connection = ProviderManager.get_connection(db, user, provider_key)
        if connection:
            connection.last_used_at = datetime.utcnow()
            db.commit()

    @staticmethod
    def get_other_enabled_provider(
        db: Session,
        user: User,
        exclude_provider: str
    ) -> Optional[str]:
        """
        Get another enabled provider, excluding the specified one.

        Useful for detecting provider switches during OAuth flows.

        Args:
            db: Database session
            user: User instance
            exclude_provider: Provider to exclude from search

        Returns:
            Provider key or None if no other provider is enabled
        """
        connection = db.query(ProviderConnection).filter(
            and_(
                ProviderConnection.user_id == user.id,
                ProviderConnection.provider_key != exclude_provider,
                ProviderConnection.is_enabled == True
            )
        ).first()

        return connection.provider_key if connection else None

    @staticmethod
    def get_connection_info(
        db: Session,
        user: User,
        provider_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get connection information for API responses.

        Args:
            db: Database session
            user: User instance
            provider_key: Provider identifier

        Returns:
            Dictionary with connection info or None
        """
        connection = ProviderManager.get_connection(db, user, provider_key)
        if not connection:
            return None

        metadata = ProviderRegistry.get(provider_key)
        return {
            'provider_key': provider_key,
            'display_name': metadata.display_name if metadata else provider_key,
            'is_enabled': connection.is_enabled,
            'is_active': connection.is_active,
            'connected_at': connection.connected_at.isoformat() if connection.connected_at else None,
            'last_used_at': connection.last_used_at.isoformat() if connection.last_used_at else None,
        }


# Singleton instance for convenience
provider_manager = ProviderManager()
