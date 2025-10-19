"""
Email Integration Manager - Fetches email configurations from Supabase.
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from config.supabase import get_supabase_client
from .oauth_helper import OAuthTokenManager

logger = logging.getLogger(__name__)


class EmailIntegration:
    """Represents an email integration from Supabase."""
    
    def __init__(self, integration_data: Dict):
        """
        Initialize email integration from Supabase data.
        
        Args:
            integration_data: Dictionary containing integration fields from api.email_integrations
        """
        self.id = integration_data.get('id')
        self.user_id = integration_data.get('user_id')
        self.integration_type = integration_data.get('integration_type')
        
        # OAuth fields
        self.oauth_provider = integration_data.get('oauth_provider')
        self.oauth_access_token = integration_data.get('oauth_access_token')
        self.oauth_refresh_token = integration_data.get('oauth_refresh_token')
        self.oauth_token_expiry = integration_data.get('oauth_token_expiry')
        self.oauth_scopes = integration_data.get('oauth_scopes', [])
        
        # Manual IMAP fields
        self.email_host = integration_data.get('email_host')
        self.email_server = integration_data.get('email_server')
        self.email_port = integration_data.get('email_port', 993)
        self.email_username = integration_data.get('email_username')
        self.email_key = integration_data.get('email_key')
        self.email_use_ssl = integration_data.get('email_use_ssl', True)
        
        # Status
        self.is_active = integration_data.get('is_active', True)
        self.last_sync_at = integration_data.get('last_sync_at')
    
    def is_oauth(self) -> bool:
        """Check if this is an OAuth integration."""
        return self.integration_type == 'oauth'
    
    def is_manual(self) -> bool:
        """Check if this is a manual IMAP integration."""
        return self.integration_type == 'manual'
    
    def get_imap_config(self) -> Dict:
        """Get IMAP configuration for this integration."""
        if self.is_oauth():
            # For OAuth (Gmail), use Gmail IMAP settings
            return {
                'server': 'imap.gmail.com',
                'port': 993,
                'use_ssl': True,
                'username': self.email_username or self.oauth_provider,  # Gmail email
                'password': self.oauth_access_token  # Use OAuth access token as password
            }
        else:
            # For manual integration
            return {
                'server': self.email_server,
                'port': self.email_port,
                'use_ssl': self.email_use_ssl,
                'username': self.email_username,
                'password': self.email_key
            }
    
    def __repr__(self):
        return f"EmailIntegration(type={self.integration_type}, user={self.user_id}, active={self.is_active})"


class EmailIntegrationManager:
    """Manages email integrations from Supabase."""
    
    def __init__(self):
        """Initialize the integration manager."""
        self.supabase = get_supabase_client(use_service_role=True, schema='api')
        self.oauth_manager = OAuthTokenManager()
    
    def get_active_oauth_integrations(self) -> List[EmailIntegration]:
        """
        Fetch all active OAuth email integrations from Supabase.
        
        Returns:
            List of EmailIntegration objects
        """
        try:
            logger.info("Fetching active OAuth integrations from Supabase...")
            
            # Query email_integrations for active OAuth integrations
            # The schema 'api' is already set in the Supabase client
            response = self.supabase.table('email_integrations') \
                .select('*') \
                .eq('integration_type', 'oauth') \
                .eq('is_active', True) \
                .execute()
            
            integrations = []
            if response.data:
                logger.info(f"Found {len(response.data)} active OAuth integrations")
                for integration_data in response.data:
                    integration = EmailIntegration(integration_data)
                    integrations.append(integration)
            else:
                logger.warning("No active OAuth integrations found in Supabase")
            
            return integrations
            
        except Exception as e:
            logger.error(f"Error fetching email integrations from Supabase: {e}")
            return []
    
    def refresh_oauth_token_if_needed(self, integration: EmailIntegration) -> bool:
        """
        Refresh OAuth token if expired and update in Supabase.
        
        Args:
            integration: EmailIntegration object
            
        Returns:
            True if token is valid/refreshed, False if refresh failed
        """
        if not integration.is_oauth():
            return True  # Not OAuth, no refresh needed
        
        # Parse expiry time
        expiry_time = None
        if integration.oauth_token_expiry:
            if isinstance(integration.oauth_token_expiry, str):
                try:
                    expiry_time = datetime.fromisoformat(integration.oauth_token_expiry.replace('Z', '+00:00'))
                except:
                    pass
            elif isinstance(integration.oauth_token_expiry, datetime):
                expiry_time = integration.oauth_token_expiry
        
        # Check if token needs refresh
        if not self.oauth_manager.is_token_expired(expiry_time):
            logger.info(f"OAuth token for integration {integration.id} is still valid")
            return True
        
        logger.info(f"OAuth token for integration {integration.id} is expired, refreshing...")
        
        # Refresh the token
        new_access_token, new_expiry, error = self.oauth_manager.refresh_access_token(
            integration.oauth_refresh_token
        )
        
        if error or not new_access_token:
            logger.error(f"Failed to refresh OAuth token: {error}")
            return False
        
        # Update in Supabase
        try:
            self.supabase.table('email_integrations') \
                .update({
                    'oauth_access_token': new_access_token,
                    'oauth_token_expiry': new_expiry.isoformat() if new_expiry else None,
                    'updated_at': datetime.utcnow().isoformat()
                }) \
                .eq('id', integration.id) \
                .execute()
            
            # Update local integration object
            integration.oauth_access_token = new_access_token
            integration.oauth_token_expiry = new_expiry
            
            logger.info(f"Successfully refreshed and updated OAuth token for integration {integration.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating refreshed token in Supabase: {e}")
            return False
    
    def update_last_sync(self, integration_id: str):
        """
        Update the last_sync_at timestamp for an integration.
        
        Args:
            integration_id: Integration ID
        """
        try:
            self.supabase.table('email_integrations') \
                .update({
                    'last_sync_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }) \
                .eq('id', integration_id) \
                .execute()
            
            logger.info(f"Updated last_sync_at for integration {integration_id}")
            
        except Exception as e:
            logger.error(f"Error updating last_sync_at: {e}")

