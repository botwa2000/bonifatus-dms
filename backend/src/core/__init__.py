# backend/src/core/__init__.py
"""
Bonifatus DMS - Core Module
Business logic and configuration management
Zero hardcoded values - all configuration from environment/database
"""

from .config import settings, get_settings

__all__ = ["settings", "get_settings"]