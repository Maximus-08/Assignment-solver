"""
Authentication manager for Google Classroom API OAuth 2.0 flow.
Handles credential management, token refresh, and authorization flow.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
import requests

from .config import settings

logger = logging.getLogger(__name__)

class AuthenticationManager:
    """Manages Google OAuth 2.0 authentication for Classroom API"""
    
    def __init__(self):
        self.credentials: Optional[Credentials] = None
        self._last_auth_attempt: Optional[datetime] = None
        self._auth_retry_count = 0
    
    def validate_credentials_file(self) -> bool:
        """
        Validate that the credentials file exists and has correct format.
        
        Returns:
            bool: True if credentials file is valid, False otherwise
        """
        try:
            credentials_path = Path(settings.GOOGLE_CREDENTIALS_FILE)
            
            if not credentials_path.exists():
                logger.error(f"Credentials file not found: {settings.GOOGLE_CREDENTIALS_FILE}")
                logger.error("Please download credentials.json from Google Cloud Console")
                return False
            
            with open(credentials_path, 'r') as f:
                creds_data = json.load(f)
            
            # Validate OAuth client credentials format
            if 'installed' not in creds_data:
                logger.error("Invalid credentials format")
                logger.error("Must be OAuth client credentials, not service account credentials")
                return False
            
            # Check required fields
            required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
            installed = creds_data['installed']
            
            missing_fields = [field for field in required_fields if field not in installed]
            if missing_fields:
                logger.error(f"Missing required fields in credentials: {missing_fields}")
                return False
            
            logger.debug("Credentials file validation passed")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format in credentials file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error validating credentials file: {e}")
            return False
    
    def load_existing_credentials(self) -> bool:
        """
        Load existing credentials from token file if available.
        
        Returns:
            bool: True if credentials loaded successfully, False otherwise
        """
        token_path = Path(settings.GOOGLE_TOKEN_FILE)
        
        if not token_path.exists():
            logger.debug("No existing token file found")
            return False
        
        try:
            self.credentials = Credentials.from_authorized_user_file(
                settings.GOOGLE_TOKEN_FILE, 
                settings.GOOGLE_SCOPES
            )
            logger.info("Existing credentials loaded successfully")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load existing credentials: {e}")
            # Remove corrupted token file
            try:
                token_path.unlink()
                logger.info("Removed corrupted token file")
            except Exception:
                pass
            return False
    
    def refresh_credentials(self) -> bool:
        """
        Refresh expired credentials using refresh token.
        
        Returns:
            bool: True if refresh successful, False otherwise
        """
        if not self.credentials:
            logger.warning("No credentials to refresh")
            return False
        
        if not self.credentials.expired:
            logger.debug("Credentials are still valid, no refresh needed")
            return True
        
        if not self.credentials.refresh_token:
            logger.warning("No refresh token available, need to re-authorize")
            return False
        
        try:
            logger.info("Refreshing expired credentials...")
            self.credentials.refresh(Request())
            self.save_credentials()
            logger.info("Credentials refreshed successfully")
            return True
            
        except RefreshError as e:
            logger.error(f"Failed to refresh credentials: {e}")
            logger.info("Credentials may have been revoked, need to re-authorize")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during credential refresh: {e}")
            return False
    
    def run_oauth_flow(self) -> bool:
        """
        Run OAuth 2.0 authorization flow to get new credentials.
        
        Returns:
            bool: True if OAuth flow successful, False otherwise
        """
        try:
            logger.info("Starting OAuth 2.0 authorization flow...")
            
            # Check retry limits
            if self._should_limit_retries():
                return False
            
            self._last_auth_attempt = datetime.now()
            self._auth_retry_count += 1
            
            # Create flow from credentials file
            flow = InstalledAppFlow.from_client_secrets_file(
                settings.GOOGLE_CREDENTIALS_FILE, 
                settings.GOOGLE_SCOPES
            )
            
            # Run local server for OAuth callback
            self.credentials = flow.run_local_server(
                port=0,
                timeout_seconds=settings.AUTH_TIMEOUT_SECONDS,
                open_browser=True
            )
            
            logger.info("OAuth 2.0 flow completed successfully")
            self.save_credentials()
            
            # Reset retry count on success
            self._auth_retry_count = 0
            return True
            
        except Exception as e:
            logger.error(f"OAuth flow failed: {e}")
            return False
    
    def save_credentials(self):
        """Save credentials to token file with backup and security measures"""
        try:
            if not self.credentials:
                logger.warning("No credentials to save")
                return
            
            token_path = Path(settings.GOOGLE_TOKEN_FILE)
            
            # Create backup of existing token file
            if token_path.exists():
                backup_path = token_path.with_suffix('.json.backup')
                try:
                    token_path.rename(backup_path)
                    logger.debug(f"Created backup: {backup_path}")
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")
            
            # Save new credentials
            with open(token_path, 'w') as token_file:
                token_file.write(self.credentials.to_json())
            
            # Set secure file permissions (owner read/write only)
            if os.name != 'nt':  # Not Windows
                os.chmod(token_path, 0o600)
            
            logger.info(f"Credentials saved to {settings.GOOGLE_TOKEN_FILE}")
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            
            # Try to restore backup if save failed
            backup_path = Path(settings.GOOGLE_TOKEN_FILE).with_suffix('.json.backup')
            if backup_path.exists():
                try:
                    backup_path.rename(settings.GOOGLE_TOKEN_FILE)
                    logger.info("Restored backup credentials file")
                except Exception as restore_error:
                    logger.error(f"Failed to restore backup: {restore_error}")
    
    def revoke_credentials(self):
        """Revoke stored credentials and clean up token files"""
        try:
            if self.credentials and hasattr(self.credentials, 'token'):
                # Revoke the token with Google
                revoke_url = 'https://oauth2.googleapis.com/revoke'
                response = requests.post(
                    revoke_url,
                    params={'token': self.credentials.token},
                    headers={'content-type': 'application/x-www-form-urlencoded'},
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info("Credentials revoked successfully with Google")
                else:
                    logger.warning(f"Failed to revoke with Google: {response.status_code}")
            
            # Remove token file
            token_path = Path(settings.GOOGLE_TOKEN_FILE)
            if token_path.exists():
                token_path.unlink()
                logger.info(f"Removed token file: {settings.GOOGLE_TOKEN_FILE}")
            
            # Remove backup file
            backup_path = token_path.with_suffix('.json.backup')
            if backup_path.exists():
                backup_path.unlink()
                logger.debug("Removed backup token file")
            
            # Clear in-memory credentials
            self.credentials = None
            self._auth_retry_count = 0
            
        except Exception as e:
            logger.error(f"Error revoking credentials: {e}")
    
    def authenticate(self) -> bool:
        """
        Main authentication method that handles the complete OAuth flow.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        logger.info("Starting Google Classroom API authentication...")
        
        try:
            # Step 1: Validate credentials file
            if not self.validate_credentials_file():
                return False
            
            # Step 2: Try to load existing credentials
            if self.load_existing_credentials():
                # Step 3: Check if credentials are valid or can be refreshed
                if self.credentials.valid:
                    logger.info("Using existing valid credentials")
                    return True
                elif self.refresh_credentials():
                    logger.info("Successfully refreshed credentials")
                    return True
            
            # Step 4: Run OAuth flow for new credentials
            if self.run_oauth_flow():
                logger.info("Authentication completed successfully")
                return True
            
            logger.error("All authentication methods failed")
            return False
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def _should_limit_retries(self) -> bool:
        """Check if authentication retries should be limited"""
        if not self._last_auth_attempt:
            return False
        
        time_since_last = datetime.now() - self._last_auth_attempt
        if time_since_last < timedelta(minutes=1) and self._auth_retry_count >= settings.AUTH_RETRY_ATTEMPTS:
            logger.error(f"Too many authentication attempts ({self._auth_retry_count}). Please wait before retrying.")
            return True
        
        return False
    
    def get_auth_status(self) -> Dict[str, Any]:
        """
        Get comprehensive authentication status information.
        
        Returns:
            Dict containing detailed authentication status
        """
        return {
            'authenticated': self.is_authenticated(),
            'credentials_file_exists': Path(settings.GOOGLE_CREDENTIALS_FILE).exists(),
            'token_file_exists': Path(settings.GOOGLE_TOKEN_FILE).exists(),
            'credentials_valid': self.credentials.valid if self.credentials else False,
            'credentials_expired': self.credentials.expired if self.credentials else None,
            'has_refresh_token': bool(self.credentials.refresh_token) if self.credentials else False,
            'scopes': settings.GOOGLE_SCOPES,
            'last_auth_attempt': self._last_auth_attempt.isoformat() if self._last_auth_attempt else None,
            'retry_count': self._auth_retry_count,
            'credentials_file_path': settings.GOOGLE_CREDENTIALS_FILE,
            'token_file_path': settings.GOOGLE_TOKEN_FILE
        }
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated with valid credentials"""
        return self.credentials is not None and self.credentials.valid
    
    def get_credentials(self) -> Optional[Credentials]:
        """Get the current credentials object"""
        return self.credentials if self.is_authenticated() else None