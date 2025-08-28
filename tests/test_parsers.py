"""
Tests for email parsers.
"""
import pytest
from email.message import Message
from email.mime.text import MIMEText

from src.email_parser.parsers.cashapp_parser import CashAppParser
from src.email_parser.parsers.base_parser import BaseParser


class TestCashAppParser:
    """Test Cash App parser functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CashAppParser()
    
    def create_test_email(self, subject: str, body: str, from_addr: str = "cash@square.com") -> Message:
        """Create a test email message."""
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = from_addr
        msg['Date'] = "Mon, 1 Jan 2024 12:00:00 +0000"
        return msg
    
    def test_can_parse_cashapp_email(self):
        """Test that Cash App emails are correctly identified."""
        email_msg = self.create_test_email(
            "Payment received from John Doe",
            "You received $25.00 from John Doe"
        )
        
        assert self.parser.can_parse(email_msg) is True
    
    def test_cannot_parse_non_cashapp_email(self):
        """Test that non-Cash App emails are rejected."""
        email_msg = self.create_test_email(
            "Regular email",
            "This is a regular email",
            "other@example.com"
        )
        
        assert self.parser.can_parse(email_msg) is False
    
    def test_parse_transaction_amount(self):
        """Test amount extraction from email."""
        email_msg = self.create_test_email(
            "Payment received",
            "You received $123.45 from Jane Smith"
        )
        
        transaction = self.parser.parse_transaction(email_msg)
        assert transaction is not None
        assert transaction["amount"] == 123.45
        assert transaction["sender"] == "Jane Smith"
    
    def test_parse_transaction_with_comma_amount(self):
        """Test amount extraction with comma formatting."""
        email_msg = self.create_test_email(
            "Payment received",
            "You received $1,234.56 from John Doe"
        )
        
        transaction = self.parser.parse_transaction(email_msg)
        assert transaction is not None
        assert transaction["amount"] == 1234.56
    
    def test_parse_transaction_sender_extraction(self):
        """Test sender extraction from email."""
        email_msg = self.create_test_email(
            "Payment received",
            "You received $50.00 from Alice Johnson"
        )
        
        transaction = self.parser.parse_transaction(email_msg)
        assert transaction is not None
        assert transaction["sender"] == "Alice Johnson"
    
    def test_parse_transaction_type_detection(self):
        """Test transaction type detection."""
        # Test received payment
        email_msg = self.create_test_email(
            "Payment received",
            "You received $25.00 from Bob"
        )
        
        transaction = self.parser.parse_transaction(email_msg)
        assert transaction is not None
        assert transaction["transaction_type"] == "received"
    
    def test_parse_transaction_with_description(self):
        """Test description extraction."""
        email_msg = self.create_test_email(
            "Payment received",
            "You received $100.00 from Charlie\nNote: Lunch payment"
        )
        
        transaction = self.parser.parse_transaction(email_msg)
        assert transaction is not None
        assert transaction["description"] == "Lunch payment"
    
    def test_parse_transaction_validation(self):
        """Test transaction data validation."""
        email_msg = self.create_test_email(
            "Payment received",
            "You received $75.00 from David"
        )
        
        transaction = self.parser.parse_transaction(email_msg)
        assert transaction is not None
        assert self.parser.validate_transaction_data(transaction) is True
    
    def test_parse_transaction_missing_amount(self):
        """Test handling of emails without amount."""
        email_msg = self.create_test_email(
            "Payment notification",
            "A payment was made but no amount specified"
        )
        
        transaction = self.parser.parse_transaction(email_msg)
        assert transaction is None
    
    def test_generate_transaction_id(self):
        """Test transaction ID generation."""
        email_msg = self.create_test_email(
            "Payment received",
            "You received $50.00 from Eve"
        )
        
        transaction_id = self.parser.generate_transaction_id(email_msg, 50.0, "Eve")
        assert transaction_id is not None
        assert len(transaction_id) == 32  # MD5 hash length
        assert isinstance(transaction_id, str)


class TestBaseParser:
    """Test base parser functionality."""
    
    def test_base_parser_abstract(self):
        """Test that BaseParser cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseParser("test")
    
    def test_base_parser_methods_exist(self):
        """Test that required methods exist in concrete implementations."""
        parser = CashAppParser()
        
        # Check that required methods exist
        assert hasattr(parser, 'can_parse')
        assert hasattr(parser, 'parse_transaction')
        assert hasattr(parser, 'extract_email_body')
        assert hasattr(parser, 'validate_transaction_data')
    
    def test_email_body_extraction(self):
        """Test email body extraction."""
        parser = CashAppParser()
        email_msg = self.create_test_email(
            "Test subject",
            "This is the email body content"
        )
        
        body = parser.extract_email_body(email_msg)
        assert "This is the email body content" in body
    
    def create_test_email(self, subject: str, body: str) -> Message:
        """Create a test email message."""
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = "test@example.com"
        msg['Date'] = "Mon, 1 Jan 2024 12:00:00 +0000"
        return msg
