# backend/src/services/google_oauth_service.py
"""
Bonifatus DMS - Google OAuth Service
Google OAuth 2.0 authentication flow implementation
Secure token management and user information retrieval
"""

import httpx
import secrets
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode
import logging
from datetime import datetime, timedelta

from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GoogleOAuthService:
    """Google OAuth 2.0 service for authentication and API access"""

    def __init__(self):
        self.client_id = settings.google.google_client_id
        self.client_secret = settings.google.google_client_secret
        self.redirect_uri = (
            settings.google.google_redirect_uri or "http://localhost:3000/auth/callback"
        )
        self.scopes = settings.google.google_drive_scopes

        # Google OAuth endpoints
        self.auth_uri = "https://accounts.google.com/o/oauth2/auth"
        self.token_uri = "https://oauth2.googleapis.com/token"
        self.userinfo_uri = "https://www.googleapis.com/oauth2/v1/userinfo"
        self.revoke_uri = "https://oauth2.googleapis.com/revoke"

        # State storage for CSRF protection
        self._state_storage = {}

    def get_authorization_url(self, force_consent: bool = False) -> Tuple[str, str]:
        """
        Generate Google OAuth authorization URL with CSRF state
        """
        try:
            # Generate secure random state for CSRF protection
            state = secrets.token_urlsafe(32)

            # Store state with timestamp for validation
            self._state_storage[state] = {
                "created_at": datetime.utcnow(),
                "used": False,
            }

            # Build authorization URL parameters
            auth_params = {
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "scope": " ".join(self.scopes),
                "state": state,
                "access_type": "offline",  # Request refresh token
                "prompt": "consent" if force_consent else "select_account",
                "include_granted_scopes": "true",
            }

            auth_url = f"{self.auth_uri}?{urlencode(auth_params)}"

            logger.info(f"Generated OAuth authorization URL with state: {state}")
            return auth_url, state

        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            raise

    def verify_state(self, state: str) -> bool:
        """
        Verify OAuth state parameter for CSRF protection
        """
        try:
            if not state or state not in self._state_storage:
                logger.warning(f"Invalid or missing state parameter: {state}")
                return False

            state_data = self._state_storage[state]

            # Check if state was already used
            if state_data["used"]:
                logger.warning(f"State parameter already used: {state}")
                return False

            # Check if state is expired (5 minutes max)
            created_at = state_data["created_at"]
            if datetime.utcnow() - created_at > timedelta(minutes=5):
                logger.warning(f"State parameter expired: {state}")
                del self._state_storage[state]
                return False

            # Mark state as used
            state_data["used"] = True
            logger.info(f"State parameter verified successfully: {state}")
            return True

        except Exception as e:
            logger.error(f"State verification failed: {e}")
            return False

    async def exchange_code_for_tokens(
        self, authorization_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access and refresh tokens
        """
        try:
            token_data = {
                "code": authorization_code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_uri,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(
                        f"Token exchange failed: {response.status_code} - {response.text}"
                    )
                    return None

                token_response = response.json()

                # Validate required fields
                if "access_token" not in token_response:
                    logger.error("No access token in response")
                    return None

                logger.info("Successfully exchanged authorization code for tokens")
                return {
                    "access_token": token_response["access_token"],
                    "refresh_token": token_response.get("refresh_token"),
                    "token_type": token_response.get("token_type", "Bearer"),
                    "expires_in": token_response.get("expires_in", 3600),
                    "scope": token_response.get("scope", ""),
                }

        except Exception as e:
            logger.error(f"Failed to exchange code for tokens: {e}")
            return None

    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from Google using access token
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}

            async with httpx.AsyncClient() as client:
                response = await client.get(self.userinfo_uri, headers=headers)

                if response.status_code != 200:
                    logger.error(
                        f"User info request failed: {response.status_code} - {response.text}"
                    )
                    return None

                user_info = response.json()

                # Validate required fields
                if "id" not in user_info or "email" not in user_info:
                    logger.error("Missing required user info fields")
                    return None

                logger.info(f"Retrieved user info for: {user_info.get('email')}")
                return {
                    "id": user_info["id"],
                    "email": user_info["email"],
                    "name": user_info.get("name", ""),
                    "given_name": user_info.get("given_name", ""),
                    "family_name": user_info.get("family_name", ""),
                    "picture": user_info.get("picture"),
                    "locale": user_info.get("locale", "en"),
                    "verified_email": user_info.get("verified_email", False),
                }

        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None

    async def refresh_access_token(
        self, refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh access token using refresh token
        """
        try:
            token_data = {
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_uri,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(
                        f"Token refresh failed: {response.status_code} - {response.text}"
                    )
                    return None

                token_response = response.json()

                if "access_token" not in token_response:
                    logger.error("No access token in refresh response")
                    return None

                logger.info("Successfully refreshed access token")
                return {
                    "access_token": token_response["access_token"],
                    "token_type": token_response.get("token_type", "Bearer"),
                    "expires_in": token_response.get("expires_in", 3600),
                    "scope": token_response.get("scope", ""),
                    # Refresh token might not be included in response
                    "refresh_token": token_response.get("refresh_token", refresh_token),
                }

        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            return None

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke access or refresh token
        """
        try:
            revoke_data = {"token": token}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.revoke_uri,
                    data=revoke_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    logger.info("Successfully revoked token")
                    return True
                else:
                    logger.warning(f"Token revocation failed: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False

    async def validate_token(self, access_token: str) -> bool:
        """
        Validate access token by making a test API call
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v1/tokeninfo",
                    headers=headers,
                    params={"access_token": access_token},
                )

                if response.status_code == 200:
                    token_info = response.json()

                    # Check if token belongs to our client
                    if token_info.get("audience") == self.client_id:
                        logger.info("Token validation successful")
                        return True
                    else:
                        logger.warning("Token belongs to different client")
                        return False
                else:
                    logger.warning(f"Token validation failed: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return False

    def cleanup_expired_states(self) -> int:
        """
        Clean up expired state parameters (housekeeping)
        """
        try:
            expired_states = []
            current_time = datetime.utcnow()

            for state, state_data in self._state_storage.items():
                if current_time - state_data["created_at"] > timedelta(minutes=5):
                    expired_states.append(state)

            for state in expired_states:
                del self._state_storage[state]

            if expired_states:
                logger.info(
                    f"Cleaned up {len(expired_states)} expired state parameters"
                )

            return len(expired_states)

        except Exception as e:
            logger.error(f"Failed to cleanup expired states: {e}")
            return 0
