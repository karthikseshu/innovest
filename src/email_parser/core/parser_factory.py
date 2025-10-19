"""
Parser factory for managing different email parsers.
"""
from typing import Dict, Type, Optional
import logging
from email.message import Message

from ..parsers.base_parser import BaseParser
from ..parsers.cashapp_parser import CashAppParser
from ..parsers.generic_payment_parser import GenericPaymentParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """Factory for creating and managing email parsers."""
    
    def __init__(self):
        self._parsers: Dict[str, BaseParser] = {}
        self._register_default_parsers()
    
    def _register_default_parsers(self):
        """Register the default parsers."""
        # Register specific parsers first (they have priority)
        self.register_parser("cashapp", CashAppParser())
        # Register generic parser last (it's the fallback)
        self.register_parser("generic_payment", GenericPaymentParser())
        logger.info("Registered default parsers (cashapp, generic_payment)")
    
    def register_parser(self, name: str, parser: BaseParser):
        """
        Register a new parser.
        
        Args:
            name: Parser name/identifier
            parser: Parser instance
        """
        if not isinstance(parser, BaseParser):
            raise ValueError("Parser must inherit from BaseParser")
        
        self._parsers[name] = parser
        logger.info(f"Registered parser: {name}")
    
    def get_parser(self, name: str) -> Optional[BaseParser]:
        """
        Get a parser by name.
        
        Args:
            name: Parser name
            
        Returns:
            Parser instance or None if not found
        """
        return self._parsers.get(name)
    
    def get_all_parsers(self) -> Dict[str, BaseParser]:
        """Get all registered parsers."""
        return self._parsers.copy()
    
    def find_parser_for_email(self, email_message: Message) -> Optional[BaseParser]:
        """
        Find the appropriate parser for a given email.
        
        Args:
            email_message: The email message to parse
            
        Returns:
            Parser instance or None if no suitable parser found
        """
        logger.info(f"Looking for parser for email from: {email_message.get('from', 'Unknown')}")
        logger.info(f"Email subject: {email_message.get('subject', 'No subject')}")
        
        for name, parser in self._parsers.items():
            try:
                logger.info(f"Testing parser '{name}'...")
                can_parse = parser.can_parse(email_message)
                logger.info(f"Parser '{name}' can_parse result: {can_parse}")
                
                if can_parse:
                    logger.info(f"Found parser '{name}' for email")
                    return parser
            except Exception as e:
                logger.warning(f"Parser '{name}' failed to check email: {e}")
                continue
        
        logger.warning("No suitable parser found for email")
        return None
    
    def list_supported_providers(self) -> list:
        """Get list of supported email providers."""
        return list(self._parsers.keys())
    
    def remove_parser(self, name: str) -> bool:
        """
        Remove a parser.
        
        Args:
            name: Parser name to remove
            
        Returns:
            True if parser was removed, False if not found
        """
        if name in self._parsers:
            del self._parsers[name]
            logger.info(f"Removed parser: {name}")
            return True
        return False


# Global parser factory instance
parser_factory = ParserFactory()
