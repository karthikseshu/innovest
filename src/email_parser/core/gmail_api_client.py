"""
Gmail API client for fetching emails using OAuth tokens.
This works with gmail.readonly scope and doesn't require IMAP access.
"""
import logging
import base64
import email
from typing import List, Optional, Generator
from email.message import Message
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GmailAPIClient:
    """Email client using Gmail API instead of IMAP."""
    
    def __init__(self, access_token: str, refresh_token: str = None):
        """
        Initialize Gmail API client.
        
        Args:
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.service = None
    
    def __enter__(self):
        """Initialize Gmail API service."""
        try:
            # Create credentials from access token
            credentials = Credentials(token=self.access_token)
            
            # Build Gmail API service
            self.service = build('gmail', 'v1', credentials=credentials)
            logger.info("Connected to Gmail API")
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to initialize Gmail API: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup Gmail API service."""
        self.service = None
        logger.info("Disconnected from Gmail API")
    
    def search_emails_by_sender(
        self, 
        sender_email: str, 
        limit: Optional[int] = None
    ) -> Generator[Message, None, None]:
        """
        Search emails by sender using Gmail API.
        
        Args:
            sender_email: Email address to search for
            limit: Maximum number of emails to fetch
            
        Yields:
            Email Message objects
        """
        try:
            # Build Gmail query
            query = f'from:{sender_email}'
            
            logger.info(f"Gmail API query: {query}, limit: {limit}")
            
            # Search for messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=limit if limit else 100
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} messages from {sender_email}")
            
            # Fetch and yield each message
            for msg_ref in messages:
                try:
                    # Get full message
                    message = self.service.users().messages().get(
                        userId='me',
                        id=msg_ref['id'],
                        format='raw'
                    ).execute()
                    
                    # Decode the raw message
                    msg_str = base64.urlsafe_b64decode(message['raw']).decode('utf-8')
                    email_message = email.message_from_string(msg_str)
                    
                    yield email_message
                    
                except Exception as e:
                    logger.warning(f"Error fetching message {msg_ref['id']}: {e}")
                    continue
                    
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            raise
    
    def search_emails_by_sender_date_range(
        self,
        sender_email: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> Generator[Message, None, None]:
        """
        Search emails by sender within a date range using Gmail API.
        
        Args:
            sender_email: Email address to search for
            start_date: Start date (timezone-aware)
            end_date: End date (timezone-aware)
            limit: Maximum number of emails to fetch
            
        Yields:
            Email Message objects
        """
        try:
            # Format dates for Gmail API (YYYY/MM/DD)
            start_date_str = start_date.strftime("%Y/%m/%d")
            
            # Build Gmail query with date range
            query = f'from:{sender_email} after:{start_date_str}'
            
            if end_date:
                # For same-day searches, use "before" with next day
                if start_date.date() == end_date.date():
                    # Same day: search from start_date to next day
                    from datetime import timedelta
                    next_day = end_date + timedelta(days=1)
                    end_date_str = next_day.strftime("%Y/%m/%d")
                    query += f' before:{end_date_str}'
                    logger.info(f"Same-day search: using next day {end_date_str}")
                else:
                    end_date_str = end_date.strftime("%Y/%m/%d")
                    query += f' before:{end_date_str}'
            
            logger.info(f"Gmail API query: {query}, limit: {limit}")
            logger.info(f"Date range: {start_date_str} to {end_date_str if end_date else 'no end date'}")
            
            # Search for messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=limit if limit else 500
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} messages from {sender_email} in date range")
            
            # If no messages found with date range, try without date range as fallback
            if len(messages) == 0:
                logger.info(f"No messages found with date range, trying without date filter...")
                fallback_query = f'from:{sender_email}'
                fallback_results = self.service.users().messages().list(
                    userId='me',
                    q=fallback_query,
                    maxResults=10  # Limit to 10 for fallback
                ).execute()
                
                fallback_messages = fallback_results.get('messages', [])
                logger.info(f"Fallback search found {len(fallback_messages)} messages from {sender_email}")
                
                if len(fallback_messages) > 0:
                    # Log the first few message IDs for debugging
                    for i, msg in enumerate(fallback_messages[:3]):
                        logger.info(f"  Message {i+1}: {msg['id']}")
            
            # Fetch and yield each message
            for msg_ref in messages:
                try:
                    # Get full message
                    message = self.service.users().messages().get(
                        userId='me',
                        id=msg_ref['id'],
                        format='raw'
                    ).execute()
                    
                    # Decode the raw message
                    msg_str = base64.urlsafe_b64decode(message['raw']).decode('utf-8')
                    email_message = email.message_from_string(msg_str)
                    
                    yield email_message
                    
                except Exception as e:
                    logger.warning(f"Error fetching message {msg_ref['id']}: {e}")
                    continue
                    
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error searching emails in date range: {e}")
            raise

