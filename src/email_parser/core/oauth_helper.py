"""
OAuth helper for refreshing Gmail access tokens.
"""
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)


class OAuthTokenManager:
    """Manages OAuth token refresh for Gmail API."""
    
    GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        """
        Initialize OAuth token manager.
        
        Args:
            client_id: Google OAuth client ID (from Supabase OAuth settings)
            client_secret: Google OAuth client secret
        """
        # These should match the credentials in Supabase Dashboard → Authentication → Providers → Google
        # For now, we'll use environment variables or hardcode for testing
        import os
        self.client_id = client_id or os.environ.get('GOOGLE_CLIENT_ID', '')
        self.client_secret = client_secret or os.environ.get('GOOGLE_CLIENT_SECRET', '')
    
    def refresh_access_token(
        self, 
        refresh_token: str
    ) -> Tuple[Optional[str], Optional[datetime], Optional[str]]:
        """
        Refresh the OAuth access token using the refresh token.
        
        Args:
            refresh_token: The OAuth refresh token
            
        Returns:
            Tuple of (new_access_token, expiry_time, error_message)
            Returns (None, None, error) if refresh fails
        """
        if not refresh_token:
            logger.error("No refresh token provided")
            return None, None, "No refresh token provided"
        
        if not self.client_id or not self.client_secret:
            logger.error("Google OAuth credentials not configured")
            return None, None, "Google OAuth credentials not configured"
        
        try:
            logger.info("Refreshing OAuth access token...")
            
            # Prepare the token refresh request
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            # Make the refresh request
            response = requests.post(
                self.GOOGLE_TOKEN_ENDPOINT,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                new_access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
                
                # Calculate expiry time with timezone awareness
                from datetime import timezone
                expiry_time = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                
                logger.info(f"Successfully refreshed access token (expires in {expires_in}s)")
                return new_access_token, expiry_time, None
            else:
                error_msg = f"Failed to refresh token: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return None, None, error_msg
                
        except Exception as e:
            error_msg = f"Exception during token refresh: {str(e)}"
            logger.error(error_msg)
            return None, None, error_msg
    
    def is_token_expired(self, expiry_time: Optional[datetime]) -> bool:
        """
        Check if the access token is expired or about to expire.
        
        Args:
            expiry_time: Token expiry datetime (UTC)
            
        Returns:
            True if token is expired or will expire in next 5 minutes
        """
        if not expiry_time:
            return True
        
        # Get current time with timezone awareness
        from datetime import timezone
        current_time = datetime.now(timezone.utc)
        
        # Ensure expiry_time is timezone-aware
        if expiry_time.tzinfo is None:
            expiry_time = expiry_time.replace(tzinfo=timezone.utc)
        
        # Add a 5-minute buffer to refresh before actual expiry
        buffer_time = timedelta(minutes=5)
        return current_time >= (expiry_time - buffer_time)

