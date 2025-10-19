"""
Base parser class for email transaction extraction.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from email.message import Message
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Abstract base class for email parsers."""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.logger = logging.getLogger(f"{__name__}.{provider_name}")
    
    @abstractmethod
    def can_parse(self, email_message: Message) -> bool:
        """
        Check if this parser can handle the given email.
        
        Args:
            email_message: The email message to check
            
        Returns:
            True if this parser can handle the email, False otherwise
        """
        pass
    
    @abstractmethod
    def parse_transaction(self, email_message: Message) -> Optional[Dict[str, Any]]:
        """
        Extract transaction details from the email.
        
        Args:
            email_message: The email message to parse
            
        Returns:
            Dictionary containing transaction details or None if parsing fails
        """
        pass
    
    def extract_email_body(self, email_message: Message) -> str:
        """
        Extract plain text body from email message.
        
        Args:
            email_message: The email message
            
        Returns:
            Plain text body content
        """
        body = ""
        
        self.logger.info(f"Email is_multipart: {email_message.is_multipart()}")
        
        if email_message.is_multipart():
            # Prefer text/plain parts
            for part in email_message.walk():
                content_type = part.get_content_type()
                self.logger.info(f"Found part with content_type: {content_type}")
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        self.logger.info(f"Extracted text/plain body (first 200 chars): {body[:200]}...")
                        break
                    except Exception as e:
                        self.logger.warning(f"Failed to decode email part: {e}")
            # If no text/plain found, try text/html and strip tags
            if not body:
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/html":
                        try:
                            raw = part.get_payload(decode=True).decode(errors="ignore")
                            # strip tags
                            import re as _re
                            from html import unescape as _unescape
                            text = _re.sub(r'<[^>]+>', ' ', raw)
                            text = _unescape(text)
                            body = _re.sub(r'\s+', ' ', text).strip()
                            break
                        except Exception as e:
                            self.logger.warning(f"Failed to decode html part: {e}")
        else:
            try:
                payload = email_message.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors="ignore")
                else:
                    # If payload is None (some libraries return str for non-multipart), try raw payload
                    raw = email_message.get_payload()
                    if isinstance(raw, str) and raw.strip():
                        body = raw
                    else:
                        # Fallback: try to extract html and strip tags
                        content_type = email_message.get_content_type()
                        if content_type == 'text/html':
                            try:
                                raw = email_message.get_payload(decode=True).decode(errors='ignore')
                                import re as _re
                                from html import unescape as _unescape
                                text = _re.sub(r'<[^>]+>', ' ', raw)
                                text = _unescape(text)
                                body = _re.sub(r'\s+', ' ', text).strip()
                            except Exception as e:
                                self.logger.warning(f"Failed to decode non-multipart html payload: {e}")
            except Exception as e:
                self.logger.warning(f"Failed to decode email payload: {e}")
        
        self.logger.info(f"Final extracted body length: {len(body)}")
        self.logger.info(f"Final extracted body (first 500 chars): {body[:500]}...")
        return body

    def extract_email_subject(self, email_message: Message) -> str:
        """Extract email subject."""
        return email_message.get("subject", "")

    def extract_email_date(self, email_message: Message) -> Optional[datetime]:
        """Extract email date."""
        date_str = email_message.get("date")
        if date_str:
            try:
                # Basic date parsing - could be enhanced with dateutil
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(date_str)
            except Exception as e:
                self.logger.warning(f"Failed to parse email date: {e}")
        return None

    def generate_transaction_id(self, email_message: Message, amount: float, sender: str) -> str:
        """
        Generate a unique transaction ID.
        
        Args:
            email_message: The email message
            amount: Transaction amount
            sender: Sender information
            
        Returns:
            Unique transaction ID
        """
        # Create a hash based on email content and key transaction details
        import hashlib
        
        content = f"{self.provider_name}:{amount}:{sender}:{self.extract_email_date(email_message)}"
        return hashlib.md5(content.encode()).hexdigest()

    def validate_transaction_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate extracted transaction data.
        
        Args:
            data: Transaction data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        required_fields = ["transaction_id", "sender", "amount", "source_provider"]
        
        for field in required_fields:
            if field not in data or data[field] is None:
                self.logger.error(f"Missing required field: {field}")
                return False
        
        if not isinstance(data["amount"], (int, float)) or data["amount"] <= 0:
            self.logger.error(f"Invalid amount: {data['amount']}")
            return False
        
        return True
