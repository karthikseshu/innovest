"""
Generic payment email parser for extracting transaction information from any payment service.
This parser attempts to extract common payment fields from emails when no specific parser matches.
"""
import re
from typing import Dict, Optional, Any
from email.message import Message
from datetime import datetime

from .base_parser import BaseParser


class GenericPaymentParser(BaseParser):
    """Generic parser for payment transaction emails from any service."""
    
    def __init__(self):
        super().__init__("generic_payment")
        
        # Generic amount patterns
        self.amount_patterns = [
            r"\$([0-9,]+\.?[0-9]*)",  # $123.45 or $1,234.56
            r"([0-9,]+\.?[0-9]*)\s*USD",  # 123.45 USD
            r"Amount[:\s]+\$?([0-9,]+\.?[0-9]*)",  # Amount: $123.45
            r"Total[:\s]+\$?([0-9,]+\.?[0-9]*)",  # Total: $123.45
        ]
        
        # Generic sender patterns
        self.sender_patterns = [
            r"([A-Za-z\s\.']+(?:\s+[A-Za-z']+)*)\s+sent\s+you",  # "John Doe sent you"
            r"sent\s+by\s+([A-Za-z\s\.']+(?:\s+[A-Za-z']+)*)",  # "sent by John Doe"
            r"from\s+([A-Za-z\s\.']+(?:\s+[A-Za-z']+)*)",  # "from John Doe"
            r"Sender[:\s]+([A-Za-z\s\.']+(?:\s+[A-Za-z']+)*)",  # "Sender: John Doe"
            r"Paid\s+by[:\s]+([A-Za-z\s\.']+)",  # "Paid by: John Doe"
        ]
        
        # Generic recipient patterns
        self.recipient_patterns = [
            r"You\s+sent\s+\$[0-9,]+\.?[0-9]*\s+to\s+([A-Za-z\s\.']+)",  # "You sent $X to Jane Doe"
            r"sent\s+to\s+([A-Za-z\s']+(?:\s+[A-Za-z']+)*)",  # "sent to Jane Doe"
            r"to\s+([A-Za-z\s']+(?:\s+[A-Za-z']+)*)",  # "to Jane Doe"
            r"Recipient[:\s]+([A-Za-z\s\.']+)",  # "Recipient: Jane Doe"
            r"Paid\s+to[:\s]+([A-Za-z\s\.']+)",  # "Paid to: Jane Doe"
        ]
        
        # Transaction number patterns
        self.transaction_patterns = [
            r"#([A-Z0-9-]+)",  # #D-QQENK44E or #ABC123
            r"Transaction\s+(?:number|ID|#)[:\s]+([#A-Z0-9-]+)",  # Transaction number: #123
            r"Reference[:\s]+([A-Z0-9-]+)",  # Reference: ABC123
            r"Confirmation[:\s]+([A-Z0-9-]+)",  # Confirmation: ABC123
        ]
    
    def can_parse(self, email_message: Message) -> bool:
        """
        Check if this is a payment email.
        This is a fallback parser, so it tries to detect payment-related keywords.
        """
        from_address = email_message.get("from", "").lower()
        subject = email_message.get("subject", "").lower()
        body = self.extract_email_body(email_message).lower()
        
        # Skip if it's from Cash App (let CashAppParser handle it)
        if "cash@square.com" in from_address:
            return False
        
        # Look for payment-related keywords
        payment_keywords = [
            "payment", "paid", "sent you", "you sent", "received", 
            "transaction", "money", "transfer", "deposit",
            "$", "usd", "amount", "total"
        ]
        
        # Check if email contains payment keywords
        keyword_count = sum(1 for keyword in payment_keywords 
                           if keyword in subject or keyword in body)
        
        # If we find at least 2 payment keywords, consider it a payment email
        if keyword_count >= 2:
            self.logger.info(f"Generic parser detected payment email from {from_address} (keywords: {keyword_count})")
            return True
        
        return False
    
    def parse_transaction(self, email_message: Message) -> Optional[Dict[str, Any]]:
        """Parse payment email and extract transaction information."""
        try:
            subject = email_message.get("subject", "")
            body = self.extract_email_body(email_message)
            
            self.logger.info(f"Generic parser parsing email: {subject}")
            self.logger.info(f"Email body length: {len(body)}")
            
            # Extract basic transaction information
            amount = self._extract_amount(body, subject)
            if not amount:
                self.logger.warning("Could not extract amount from email")
                return None
            
            # Extract sender and recipient
            sender = self._extract_sender(body, subject)
            recipient = self._extract_recipient(body, subject)
            
            # Determine who sent/received based on email content
            if not sender:
                # Check if "you sent" pattern exists
                if re.search(r"you\s+sent", body + " " + subject, re.IGNORECASE):
                    sender = "You"
                else:
                    sender = "Unknown"
            
            if not recipient:
                # Check if "sent you" pattern exists
                if re.search(r"sent\s+you", body + " " + subject, re.IGNORECASE):
                    recipient = "You"
                else:
                    recipient = "Unknown"
            
            self.logger.info(f"Extracted sender: {sender}, recipient: {recipient}")
            
            # Extract additional details
            transaction_number = self._extract_transaction_number(body, subject)
            
            # Determine transaction type
            transaction_type = self._determine_transaction_type(body, subject)
            
            # Generate transaction ID
            email_date = self._extract_email_date(email_message)
            transaction_id = self._generate_transaction_id(sender, recipient, amount, email_date)
            
            # Build transaction data
            transaction_data = {
                'transaction_id': transaction_id,
                'sender': sender,
                'recipient': recipient,
                'amount': amount,
                'currency': 'USD',
                'transaction_type': transaction_type,
                'status': 'completed',
                'description': self._extract_description(body, subject),
                'email_subject': subject,
                'email_date': email_date,
                'source_provider': self._detect_provider(email_message),
                'raw_email_data': body[:1000],  # Store first 1000 chars
                'deposited_to': 'Unknown',
                'cashapp_transaction_number': transaction_number,
            }
            
            self.logger.info(f"Generic parser built transaction data: {transaction_data}")
            
            # Create Transaction-like object (dictionary)
            from ..models.transaction import Transaction
            transaction = Transaction(**transaction_data)
            self.logger.info("Generic parser: Transaction parsing successful")
            
            return transaction
            
        except Exception as e:
            self.logger.error(f"Generic parser error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def _detect_provider(self, email_message: Message) -> str:
        """Detect payment provider from email address."""
        from_address = email_message.get("from", "").lower()
        
        # Try to detect provider from email domain
        if "venmo" in from_address:
            return "venmo"
        elif "zelle" in from_address:
            return "zelle"
        elif "paypal" in from_address:
            return "paypal"
        elif "square" in from_address:
            return "square"
        else:
            # Extract domain name
            match = re.search(r'@([a-z0-9.-]+)', from_address)
            if match:
                domain = match.group(1)
                # Get the main part before .com, .net, etc.
                provider = domain.split('.')[0]
                return provider
            return "unknown"
    
    def _extract_amount(self, body: str, subject: str) -> Optional[float]:
        """Extract transaction amount from email content."""
        content = body + " " + subject
        
        for pattern in self.amount_patterns:
            match = re.search(pattern, content)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    self.logger.info(f"Extracted amount: {amount}")
                    return amount
                except ValueError:
                    continue
        
        return None
    
    def _extract_sender(self, body: str, subject: str) -> Optional[str]:
        """Extract sender information from email content."""
        content = body + " " + subject
        
        # Check for "You sent" pattern first
        if re.search(r"you\s+sent\s+\$", content, re.IGNORECASE):
            return "You"
        
        for pattern in self.sender_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                sender = match.group(1).strip()
                sender = self._clean_name(sender)
                
                if sender and len(sender) > 2 and len(sender) < 100:
                    self.logger.info(f"Found sender with pattern '{pattern}': '{sender}'")
                    return sender
        
        return None
    
    def _extract_recipient(self, body: str, subject: str) -> Optional[str]:
        """Extract recipient information from email content."""
        content = body + " " + subject
        
        # Check for "sent you" pattern first
        if re.search(r"sent\s+you\s+\$", content, re.IGNORECASE):
            return "You"
        
        for pattern in self.recipient_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                recipient = match.group(1).strip()
                recipient = self._clean_name(recipient)
                
                if recipient and len(recipient) > 2 and len(recipient) < 100:
                    self.logger.info(f"Found recipient with pattern '{pattern}': '{recipient}'")
                    return recipient
        
        return None
    
    def _clean_name(self, name: str) -> str:
        """Clean up extracted names by removing unwanted content."""
        if not name:
            return name
        
        # Remove everything after newline/carriage return
        name = re.sub(r'\r?\n.*$', '', name).strip()
        
        # Remove any trailing punctuation
        name = re.sub(r'[^\w\s\'-]+$', '', name).strip()
        
        # Remove multiple spaces
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Filter out common unwanted words
        unwanted = ["view", "receipt", "click", "here", "visit", "url", "http"]
        name_lower = name.lower()
        if any(word in name_lower for word in unwanted):
            return name.split()[0] if name.split() else name
        
        return name
    
    def _extract_transaction_number(self, body: str, subject: str) -> Optional[str]:
        """Extract transaction number from email content."""
        content = body + " " + subject
        
        for pattern in self.transaction_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                transaction_number = match.group(1).strip()
                if not transaction_number.startswith('#'):
                    transaction_number = '#' + transaction_number
                self.logger.info(f"Found transaction number: {transaction_number}")
                return transaction_number
        
        return None
    
    def _determine_transaction_type(self, body: str, subject: str) -> str:
        """Determine the type of transaction."""
        content = (body + " " + subject).lower()
        
        if re.search(r"you\s+sent", content):
            return "sent"
        elif re.search(r"sent\s+you", content):
            return "received"
        elif re.search(r"payment\s+request", content):
            return "request"
        elif re.search(r"refund", content):
            return "refund"
        else:
            return "transfer"
    
    def _extract_description(self, body: str, subject: str) -> Optional[str]:
        """Extract transaction description if available."""
        description_patterns = [
            r"(?:note|memo|description|for|message)[:\s]+([^\n\r]+)",
        ]
        
        content = body + " " + subject
        
        for pattern in description_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                description = match.group(1).strip()
                if description and len(description) > 3 and len(description) < 200:
                    return description
        
        return None
    
    def _extract_email_date(self, email_message: Message) -> datetime:
        """Extract email date."""
        date_str = email_message.get("date")
        if date_str:
            try:
                from dateutil import parser
                return parser.parse(date_str)
            except Exception as e:
                self.logger.warning(f"Failed to parse email date: {e}")
        
        return datetime.now()
    
    def _generate_transaction_id(self, sender: str, recipient: str, amount: float, 
                                  date: Optional[datetime]) -> str:
        """Generate a unique transaction ID."""
        import hashlib
        
        unique_string = f"{sender}_{recipient}_{amount}_{date}"
        hash_object = hashlib.md5(unique_string.encode())
        return hash_object.hexdigest()

