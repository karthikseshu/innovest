"""
Email client for fetching emails from IMAP servers.
"""
import imaplib
import email
import logging
from typing import List, Optional, Generator
from email.message import Message
from contextlib import contextmanager
from datetime import datetime

from config.settings import settings

logger = logging.getLogger(__name__)


class EmailClient:
    """Email client for connecting to IMAP servers."""
    
    def __init__(self, server: str = None, port: int = None, use_ssl: bool = None, 
                 username: str = None, password: str = None):
        """
        Initialize email client.
        
        Args:
            server: IMAP server address (optional, uses settings if not provided)
            port: IMAP port (optional, uses settings if not provided)
            use_ssl: Whether to use SSL (optional, uses settings if not provided)
            username: Email username (optional, uses settings if not provided)
            password: Email password/access token (optional, uses settings if not provided)
        """
        self._connection = None
        # Store custom credentials if provided
        self._server = server
        self._port = port
        self._use_ssl = use_ssl
        self._username = username
        self._password = password
    
    def __enter__(self):
        """Connect to email server."""
        try:
            # Use custom credentials if provided, otherwise fall back to settings
            if self._server and self._username and self._password:
                server = self._server
                port = self._port or 993
                use_ssl = self._use_ssl if self._use_ssl is not None else True
                username = self._username
                password = self._password
            else:
                # Get email server configuration from settings
                email_config = settings.email_server_config
                server = email_config['server']
                port = email_config['port']
                use_ssl = email_config['use_ssl']
                username = settings.email_username
                password = settings.email_password
            
            logger.info(f"Connecting to {server}:{port}")
            
            if use_ssl:
                self._connection = imaplib.IMAP4_SSL(server, port)
            else:
                self._connection = imaplib.IMAP4(server, port)
            
            # Login with credentials
            self._connection.login(username, password)
            logger.info(f"Connected to {server}:{port}")
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to connect to email server: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Disconnect from email server."""
        if hasattr(self, '_connection') and self._connection:
            try:
                self._connection.logout()
                logger.info(f"Disconnected from email server")
            except Exception as e:
                logger.warning(f"Error during logout: {e}")
            finally:
                self._connection = None
    
    def disconnect(self):
        """Disconnect from email server."""
        if hasattr(self, '_connection') and self._connection:
            try:
                self._connection.logout()
                logger.info(f"Disconnected from email server")
            except Exception as e:
                logger.warning(f"Error during logout: {e}")
            finally:
                self._connection = None
    
    def is_connected(self) -> bool:
        """Check if connected to the server."""
        return self._connection is not None
    
    def select_mailbox(self, mailbox: str = "INBOX") -> bool:
        """
        Select a mailbox.
        
        Args:
            mailbox: Mailbox name to select
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to email server")
            return False
        
        try:
            status, messages = self._connection.select(mailbox)
            if status == "OK":
                logger.info(f"Selected mailbox: {mailbox}")
                return True
            else:
                logger.error(f"Failed to select mailbox {mailbox}: {status}")
                return False
        except Exception as e:
            logger.error(f"Error selecting mailbox: {e}")
            return False
    
    def search_emails(self, criteria: str = "UNSEEN") -> List[str]:
        """
        Search for emails matching criteria.
        
        Args:
            criteria: IMAP search criteria
            
        Returns:
            List of email message numbers
        """
        if not self.is_connected():
            logger.error("Not connected to email server")
            return []
        
        try:
            status, messages = self._connection.search(None, criteria)
            if status == "OK":
                message_numbers = messages[0].decode().split()
                logger.info(f"Found {len(message_numbers)} emails matching criteria: {criteria}")
                return message_numbers
            else:
                logger.error(f"Search failed: {status}")
                return []
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    def extract_email_body(self, email_message: Message) -> str:
        """
        Extract plain text body from email message.
        
        Args:
            email_message: The email message
            
        Returns:
            Plain text body content
        """
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to decode email part: {e}")
        else:
            try:
                payload = email_message.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors="ignore")
            except Exception as e:
                logger.warning(f"Failed to decode email payload: {e}")
        
        return body
    
    def search_emails_by_subject(self, search_text: str, limit: Optional[int] = None) -> Generator[Message, None, None]:
        """
        Search for emails with specific text in subject line.
        This is much faster than content search since it only checks subject headers.
        
        Args:
            search_text: Text to search for in email subject
            limit: Maximum number of emails to return
            
        Yields:
            Email message objects
        """
        if not self.select_mailbox():
            return
        
        try:
            # Search by subject using IMAP SEARCH (much faster)
            search_criteria = f'SUBJECT "{search_text}"'
            status, messages = self._connection.search(None, search_criteria)
            
            if status != "OK":
                logger.error(f"Subject search failed: {status}")
                return
            
            message_numbers = messages[0].decode().split()
            total_found = len(message_numbers)
            
            if limit:
                message_numbers = message_numbers[-limit:]
                logger.info(f"Limited to last {limit} emails out of {total_found} found by subject")
            
            logger.info(f"Found {len(message_numbers)} emails with '{search_text}' in subject")
            
            for message_num in message_numbers:
                email_msg = self.fetch_email(message_num)
                if email_msg:
                    yield email_msg
                    # Mark as read to prevent reprocessing
                    self.mark_as_read(message_num)
            
        except Exception as e:
            logger.error(f"Error searching emails by subject: {e}")
    
    def search_emails_by_content(self, search_text: str, limit: Optional[int] = None) -> Generator[Message, None, None]:
        """
        Search for emails containing specific text in subject or body.
        This is useful for finding forwarded emails or emails with specific content.
        
        Args:
            search_text: Text to search for in email subject or body
            limit: Maximum number of emails to return
            
        Yields:
            Email message objects
        """
        if not self.select_mailbox():
            return
        
        try:
            # First, get all emails (we'll filter by content)
            status, messages = self._connection.search(None, "ALL")
            if status != "OK":
                logger.error(f"Search failed: {status}")
                return
            
            message_numbers = messages[0].decode().split()
            total_emails = len(message_numbers)
            
            # Apply limit - search most recent emails first
            if limit:
                message_numbers = message_numbers[-limit:]  # Get most recent emails
                logger.info(f"Limited search to last {limit} emails out of {total_emails} total")
            else:
                # Default to last 100 emails if no limit specified
                message_numbers = message_numbers[-100:]
                logger.info(f"No limit specified, defaulting to last 100 emails out of {total_emails} total")
            
            emails_to_search = len(message_numbers)
            logger.info(f"Searching {emails_to_search} emails for content: '{search_text}'")
            
            found_count = 0
            processed_count = 0
            
            for i, message_num in enumerate(message_numbers):
                processed_count += 1
                
                # Log progress every 10 emails
                if processed_count % 10 == 0:
                    logger.info(f"Progress: {processed_count}/{emails_to_search} emails processed, {found_count} found")
                
                email_msg = self.fetch_email(message_num)
                if email_msg:
                    # Check if search text is in subject or body
                    subject = email_msg.get("subject", "").lower()
                    body = self.extract_email_body(email_msg).lower()
                    search_lower = search_text.lower()
                    
                    if search_lower in subject or search_lower in body:
                        found_count += 1
                        logger.info(f"Found email #{found_count}: Subject: {email_msg.get('subject', 'No subject')}")
                        yield email_msg
                        
                        # Mark as read to prevent reprocessing
                        self.mark_as_read(message_num)
                        
                        # If we found enough emails, we can stop early
                        if limit and found_count >= limit:
                            logger.info(f"Found {found_count} emails, stopping search")
                            break
            
            logger.info(f"Search complete: {found_count} emails found out of {emails_to_search} processed")
            
        except Exception as e:
            logger.error(f"Error searching emails by content: {e}")
    
    def fetch_email(self, message_num: str) -> Optional[Message]:
        """
        Fetch a single email by message number.
        
        Args:
            message_num: Message number to fetch
            
        Returns:
            Email message object or None if failed
        """
        if not self.is_connected():
            logger.error("Not connected to email server")
            return None
        
        try:
            status, data = self._connection.fetch(message_num, "(RFC822)")
            if status == "OK" and data:
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                return msg
            else:
                logger.warning(f"Failed to fetch email {message_num}: {status}")
                return None
        except Exception as e:
            logger.error(f"Error fetching email {message_num}: {e}")
            return None
    
    def mark_as_read(self, message_num: str) -> bool:
        """
        Mark an email as read.
        
        Args:
            message_num: Message number to mark
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Not connected to email server")
            return False
        
        try:
            status, _ = self._connection.store(message_num, '+FLAGS', '\\Seen')
            if status == "OK":
                logger.debug(f"Marked email {message_num} as read")
                return True
            else:
                logger.warning(f"Failed to mark email {message_num} as read: {status}")
                return False
        except Exception as e:
            logger.error(f"Error marking email {message_num} as read: {e}")
            return False
    
    def fetch_unread_emails(self, limit: Optional[int] = None) -> Generator[Message, None, None]:
        """
        Fetch unread emails.
        
        Args:
            limit: Maximum number of emails to process (None for all)
            
        Yields:
            Email message objects
        """
        if not self.select_mailbox():
            return
        
        message_numbers = self.search_emails("UNSEEN")
        
        if limit:
            message_numbers = message_numbers[:limit]
        
        for message_num in message_numbers:
            email_msg = self.fetch_email(message_num)
            if email_msg:
                yield email_msg
                # Mark as read to prevent reprocessing
                self.mark_as_read(message_num)
    
    def fetch_emails_by_sender(self, sender: str, limit: Optional[int] = None) -> Generator[Message, None, None]:
        """
        Fetch emails from a specific sender.
        
        Args:
            sender: Sender email address or domain
            limit: Maximum number of emails to fetch
            
        Yields:
            Email message objects
        """
        if not self.select_mailbox():
            return
        
        criteria = f'FROM "{sender}"'
        message_numbers = self.search_emails(criteria)
        
        if limit:
            message_numbers = message_numbers[:limit]
        
        for message_num in message_numbers:
            email_msg = self.fetch_email(message_num)
            if email_msg:
                yield email_msg
    
    def get_mailbox_info(self) -> Optional[dict]:
        """
        Get information about the current mailbox.
        
        Returns:
            Dictionary with mailbox information or None if failed
        """
        if not self.is_connected():
            return None
        
        try:
            status, messages = self._connection.status("INBOX", "(MESSAGES UNSEEN)")
            if status == "OK":
                # Parse the response to extract counts
                response = messages[0].decode()
                # Extract message counts using regex
                import re
                total_match = re.search(r'MESSAGES\s+(\d+)', response)
                unseen_match = re.search(r'UNSEEN\s+(\d+)', response)
                
                total = int(total_match.group(1)) if total_match else 0
                unseen = int(unseen_match.group(1)) if unseen_match else 0
                
                return {
                    "total_messages": total,
                    "unread_messages": unseen,
                    "read_messages": total - unseen
                }
        except Exception as e:
            logger.error(f"Error getting mailbox info: {e}")
        
        return None

    def search_emails_by_sender(self, sender_email: str, limit: Optional[int] = None) -> Generator[Message, None, None]:
        """Search emails by sender email address."""
        if not self.select_mailbox():
            return
            
        try:
            # Search by FROM header - try multiple approaches for Gmail compatibility
            search_criteria = f'FROM "{sender_email}"'
            logger.info(f"Search criteria: {search_criteria}")
            email_ids = self._connection.search(None, search_criteria)
            
            logger.info(f"Raw search response: {email_ids}")
            
            # If no results, try alternative search methods
            if not email_ids[1]:
                logger.info("Trying alternative search methods...")
                
                # Try without quotes
                alt_criteria = f'FROM {sender_email}'
                logger.info(f"Alternative search criteria: {alt_criteria}")
                email_ids = self._connection.search(None, alt_criteria)
                logger.info(f"Alternative search response: {email_ids}")
                
                # If still no results, try just the domain
                if not email_ids[1]:
                    domain = sender_email.split('@')[1] if '@' in sender_email else sender_email
                    domain_criteria = f'FROM "@{domain}"'
                    logger.info(f"Domain search criteria: {domain_criteria}")
                    email_ids = self._connection.search(None, domain_criteria)
                    logger.info(f"Domain search response: {email_ids}")
            
            if not email_ids[1]:
                logger.info(f"No emails found from {sender_email} using any search method")
                return
            
            # Handle IMAP response - Gmail returns space-separated email IDs
            if isinstance(email_ids[1], bytes):
                # Gmail returns: b'46 52 53 63 65 69...'
                raw_response = email_ids[1].decode()
                logger.info(f"Raw decoded response: '{raw_response}'")
                email_id_list = raw_response.strip().split()
            else:
                email_id_list = str(email_ids[1]).strip().split()
            
            logger.info(f"Email ID list after split: {email_id_list[:10]}...")
            
            # Clean up email IDs - remove any extra characters and keep only numeric IDs
            cleaned_email_ids = []
            for eid in email_id_list:
                eid = eid.strip()
                # Remove any non-numeric characters and keep only the email ID number
                clean_id = ''.join(c for c in eid if c.isdigit())
                if clean_id:  # Only add if we have a valid numeric ID
                    cleaned_email_ids.append(clean_id)
            
            email_id_list = cleaned_email_ids
            total_emails = len(email_id_list)
            
            # Apply limit if specified
            if limit and limit > 0:
                email_id_list = email_id_list[-limit:]  # Get last N emails
                logger.info(f"Limited to last {limit} emails out of {total_emails} valid email IDs found from {sender_email}")
            else:
                logger.info(f"Found {total_emails} valid email IDs from {sender_email}")
            
            for email_id in email_id_list:
                try:
                    email_data = self._connection.fetch(email_id, '(RFC822)')[1][0][1]
                    email_message = email.message_from_bytes(email_data)
                    yield email_message
                except Exception as e:
                    logger.warning(f"Error fetching email {email_id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error searching emails by sender {sender_email}: {e}")
            raise
    
    def search_emails_by_sender_date_range(self, sender_email: str, start_date: datetime, end_date: Optional[datetime] = None) -> Generator[Message, None, None]:
        """Search emails by sender email within a date range."""
        if not self.select_mailbox():
            return
            
        try:
            # Format dates for IMAP search - Gmail expects DD-MMM-YYYY format
            start_date_str = start_date.strftime("%d-%b-%Y")
            if end_date:
                end_date_str = end_date.strftime("%d-%b-%Y")
                search_criteria = f'FROM "{sender_email}" SINCE {start_date_str} BEFORE {end_date_str}'
            else:
                search_criteria = f'FROM "{sender_email}" SINCE {start_date_str}'
            
            logger.info(f"Search criteria: {search_criteria}")
            email_ids = self._connection.search(None, search_criteria)
            
            logger.info(f"Raw search response: {email_ids}")
            
            if not email_ids[1]:
                logger.info(f"No emails found from {sender_email} in date range")
                return
            
            # Handle both bytes and string responses
            if isinstance(email_ids[1], bytes):
                email_id_list = email_ids[1].decode().split()
            else:
                email_id_list = str(email_ids[1]).split()
            
            # Filter out empty strings only - Gmail email IDs are valid even if they contain spaces
            email_id_list = [eid.strip() for eid in email_id_list if eid.strip()]
            total_emails = len(email_id_list)
            logger.info(f"Found {total_emails} valid email IDs from {sender_email} in date range")
            
            for email_id in email_id_list:
                try:
                    email_data = self._connection.fetch(email_id, '(RFC822)')[1][0][1]
                    email_message = email.message_from_bytes(email_data)
                    yield email_message
                except Exception as e:
                    logger.warning(f"Error fetching email {email_id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error searching emails by sender {sender_email} in date range: {e}")
            raise
    
    def search_emails_by_content_date_range(self, search_text: str, start_date: datetime, end_date: Optional[datetime] = None) -> Generator[Message, None, None]:
        """Search emails by content within a date range."""
        if not self.select_mailbox():
            return
            
        try:
            # Format dates for IMAP search
            start_date_str = start_date.strftime("%d-%b-%Y")
            if end_date:
                end_date_str = end_date.strftime("%d-%b-%Y")
                search_criteria = f'SINCE {start_date_str} BEFORE {end_date_str}'
            else:
                search_criteria = f'SINCE {start_date_str}'
            
            email_ids = self._connection.search(None, search_criteria)
            
            if not email_ids[1]:
                logger.info(f"No emails found with '{search_text}' in date range")
                return
            
            # Handle both bytes and string responses
            if isinstance(email_ids[1], bytes):
                email_id_list = email_ids[1].decode().split()
            else:
                email_id_list = str(email_ids[1]).split()
            
            # Filter out empty strings only - Gmail email IDs are valid even if they contain spaces
            email_id_list = [eid.strip() for eid in email_id_list if eid.strip()]
            total_emails = len(email_id_list)
            logger.info(f"Found {total_emails} valid email IDs in date range, searching for '{search_text}'")
            
            processed = 0
            for email_id in email_id_list:
                try:
                    email_data = self._connection.fetch(email_id, '(RFC822)')[1][0][1]
                    email_message = email.message_from_bytes(email_data)
                    
                    # Check if email contains search text
                    if self._email_contains_text(email_message, search_text):
                        yield email_message
                        processed += 1
                        
                        # Log progress every 100 emails
                        if processed % 100 == 0:
                            logger.info(f"Processed {processed} matching emails...")
                            
                except Exception as e:
                    logger.warning(f"Error fetching email {email_id}: {e}")
                    continue
            
            logger.info(f"Found {processed} emails containing '{search_text}' in date range")
                    
        except Exception as e:
            logger.error(f"Error searching emails by content '{search_text}' in date range: {e}")
            raise
    
    def _email_contains_text(self, email_message: Message, search_text: str) -> bool:
        """Check if email contains the specified text in subject or body."""
        subject = email_message.get("subject", "").lower()
        body = self.extract_email_body(email_message).lower()
        search_text_lower = search_text.lower()
        
        return search_text_lower in subject or search_text_lower in body
