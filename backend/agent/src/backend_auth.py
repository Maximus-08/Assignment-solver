"""
Backend token authentication for agent.
Fetches user's Google OAuth tokens from backend instead of using credentials.json
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from google.oauth2.credentials import Credentials

from .backend_client import BackendClient

logger = logging.getLogger(__name__)

class BackendAuthManager:
    """Manages authentication by fetching user tokens from backend"""
    
    def __init__(self, backend_client: BackendClient):
        self.backend_client = backend_client
        self.credentials: Optional[Credentials] = None
        
    async def get_user_credentials(self, user_id: str) -> Optional[Credentials]:
        """
        Fetch user's Google OAuth credentials from backend.
        
        Args:
            user_id: The user ID to fetch credentials for
            
        Returns:
            Google Credentials object or None if not available
        """
        try:
            logger.info(f"Fetching Google credentials for user {user_id} from backend")
            
            # Fetch credentials from backend
            response = await self.backend_client.get_user_google_credentials(user_id)
            
            if not response or not response.get('google_access_token'):
                logger.warning(f"No Google credentials found for user {user_id}")
                return None
            
            # Create Google Credentials object
            credentials = Credentials(
                token=response['google_access_token'],
                refresh_token=response.get('google_refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=None,  # Not needed for token-based auth
                client_secret=None,  # Not needed for token-based auth
            )
            
            # Check if token is expired
            if response.get('token_expires_at'):
                expires_at = datetime.fromisoformat(response['token_expires_at'].replace('Z', '+00:00'))
                if expires_at < datetime.now(expires_at.tzinfo):
                    logger.warning(f"Token for user {user_id} is expired")
                    # Token refresh would happen automatically when using the credentials
            
            self.credentials = credentials
            logger.info(f"Successfully retrieved credentials for user {user_id}")
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to fetch user credentials: {e}")
            return None
    
    async def get_all_user_credentials(self) -> Dict[str, Credentials]:
        """
        Fetch Google credentials for all users in the system.
        
        Returns:
            Dictionary mapping user_id to Credentials
        """
        try:
            # Get list of all users from backend
            users = await self.backend_client.get_all_users()
            
            credentials_map = {}
            for user in users:
                user_id = user['id']
                creds = await self.get_user_credentials(user_id)
                if creds:
                    credentials_map[user_id] = creds
            
            logger.info(f"Retrieved credentials for {len(credentials_map)} users")
            return credentials_map
            
        except Exception as e:
            logger.error(f"Failed to fetch all user credentials: {e}")
            return {}
