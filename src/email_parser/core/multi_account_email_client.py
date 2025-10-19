"""
Multi-account email client that processes emails from multiple integrations.
"""
import logging
from typing import List, Generator, Optional
from email.message import Message
from datetime import datetime

from .email_integration_manager import EmailIntegrationManager, EmailIntegration
from .email_client import EmailClient
from .gmail_api_client import GmailAPIClient

logger = logging.getLogger(__name__)


class MultiAccountEmailClient:
    """Email client that processes emails from multiple Supabase integrations."""
    
    def __init__(self):
        """Initialize multi-account email client."""
        self.integration_manager = EmailIntegrationManager()
    
    def get_active_integrations(self) -> List[EmailIntegration]:
        """
        Get all active OAuth integrations from Supabase.
        
        Returns:
            List of EmailIntegration objects
        """
        return self.integration_manager.get_active_oauth_integrations()
    
    def process_integration_emails(
        self,
        integration: EmailIntegration,
        sender_email: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> Generator[Message, None, None]:
        """
        Process emails from a single integration.
        
        Args:
            integration: EmailIntegration object
            sender_email: Email address to search for (e.g., "cash@square.com")
            start_date: Start date for email search (optional)
            end_date: End date for email search (optional)
            limit: Maximum number of emails to fetch (optional)
            
        Yields:
            Email Message objects
        """
        logger.info(f"Processing emails for integration {integration.id} (user: {integration.user_id})")
        
        # Refresh OAuth token if needed
        if integration.is_oauth():
            if not self.integration_manager.refresh_oauth_token_if_needed(integration):
                logger.error(f"Failed to refresh OAuth token for integration {integration.id}, skipping")
                return
            
            # Check OAuth scopes
            if integration.oauth_scopes:
                logger.info(f"OAuth scopes for {integration.email_username}: {integration.oauth_scopes}")
                if 'https://mail.google.com/' not in integration.oauth_scopes:
                    logger.warning(f"⚠️  Integration {integration.email_username} may not have IMAP access scope")
                    logger.warning(f"   Current scopes: {integration.oauth_scopes}")
                    logger.warning(f"   Required: https://mail.google.com/ (full Gmail access)")
        
        # Use Gmail API for OAuth integrations, IMAP for manual integrations
        client = None
        
        try:
            if integration.is_oauth():
                # Use Gmail API for OAuth integrations (works with gmail.readonly scope)
                logger.info(f"Using Gmail API for OAuth integration: {integration.email_username}")
                client = GmailAPIClient(
                    access_token=integration.oauth_access_token,
                    refresh_token=integration.oauth_refresh_token
                )
                client.__enter__()
                
                # Search for emails using Gmail API
                if start_date and end_date:
                    logger.info(f"Gmail API: Searching emails from {sender_email} between {start_date} and {end_date}")
                    emails = client.search_emails_by_sender_date_range(
                        sender_email=sender_email,
                        start_date=start_date,
                        end_date=end_date,
                        limit=limit
                    )
                else:
                    logger.info(f"Gmail API: Searching emails from {sender_email}, limit: {limit}")
                    emails = client.search_emails_by_sender(
                        sender_email=sender_email,
                        limit=limit
                    )
            else:
                # Use IMAP for manual integrations
                logger.info(f"Using IMAP for manual integration: {integration.email_username}")
                imap_config = integration.get_imap_config()
                
                client = EmailClient(
                    server=imap_config['server'],
                    port=imap_config['port'],
                    use_ssl=imap_config['use_ssl'],
                    username=imap_config['username'],
                    password=imap_config['password']
                )
                client.__enter__()
                
                # Search for emails using IMAP
                if start_date and end_date:
                    logger.info(f"IMAP: Searching emails from {sender_email} between {start_date} and {end_date}")
                    emails = client.search_emails_by_sender_date_range(
                        sender_email=sender_email,
                        start_date=start_date,
                        end_date=end_date,
                        limit=limit
                    )
                elif limit:
                    logger.info(f"IMAP: Searching last {limit} emails from {sender_email}")
                    emails = client.search_emails_by_sender(
                        sender_email=sender_email,
                        limit=limit
                    )
                else:
                    logger.info(f"IMAP: Searching all emails from {sender_email}")
                    emails = client.search_emails_by_sender(sender_email=sender_email)
            
            # Yield emails
            email_count = 0
            for email_msg in emails:
                yield email_msg
                email_count += 1
            
            logger.info(f"Processed {email_count} emails from integration {integration.id}")
            
            # Update last sync time
            self.integration_manager.update_last_sync(integration.id)
            
        except Exception as e:
            logger.error(f"Error processing emails for integration {integration.id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # Disconnect
            if client:
                try:
                    client.__exit__(None, None, None)
                except:
                    pass
    
    def process_all_integrations_emails(
        self,
        sender_email: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> Generator[tuple[EmailIntegration, Message], None, None]:
        """
        Process emails from all active integrations.
        
        Args:
            sender_email: Email address to search for (e.g., "cash@square.com")
            start_date: Start date for email search (optional)
            end_date: End date for email search (optional)
            limit: Maximum number of emails to fetch per integration (optional)
            
        Yields:
            Tuples of (EmailIntegration, email Message)
        """
        # Get all active integrations
        integrations = self.get_active_integrations()
        
        if not integrations:
            logger.warning("No active email integrations found")
            return
        
        logger.info(f"Processing emails from {len(integrations)} active integrations")
        
        # Process each integration
        for integration in integrations:
            try:
                for email_msg in self.process_integration_emails(
                    integration=integration,
                    sender_email=sender_email,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                ):
                    yield integration, email_msg
                    
            except Exception as e:
                logger.error(f"Error processing integration {integration.id}: {e}")
                continue

