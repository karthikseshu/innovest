"""
Multi-account transaction processor for processing emails from Supabase integrations.
"""
import logging
import traceback
from typing import Dict, Any, Optional, List
from email.message import Message
from datetime import datetime

from .multi_account_email_client import MultiAccountEmailClient
from .parser_factory import parser_factory
from .email_integration_manager import EmailIntegration

logger = logging.getLogger(__name__)


class MultiAccountTransactionProcessor:
    """Transaction processor that handles multiple email accounts from Supabase."""
    
    def __init__(self):
        """Initialize the multi-account processor."""
        self.email_client = MultiAccountEmailClient()
        self.parser_factory = parser_factory
    
    def _process_email(self, email_msg: Message, integration: EmailIntegration) -> Optional[Dict[str, Any]]:
        """
        Process a single email message and extract transaction data.
        
        Args:
            email_msg: Email message to process
            integration: EmailIntegration that this email came from
            
        Returns:
            Transaction dictionary or None if processing failed
        """
        try:
            # Find appropriate parser
            parser = self.parser_factory.find_parser_for_email(email_msg)
            
            if not parser:
                logger.warning(f"No parser found for email from {email_msg.get('from', 'unknown')}")
                return None
            
            # Parse transaction
            transaction = parser.parse_transaction(email_msg)
            
            if not transaction:
                logger.warning("Parser returned empty transaction")
                return None
            
            # Add integration metadata
            transaction_dict = transaction.__dict__ if hasattr(transaction, '__dict__') else transaction
            transaction_dict['integration_id'] = integration.id
            transaction_dict['integration_user_id'] = integration.user_id
            
            return transaction_dict
            
        except Exception as e:
            logger.error(f"Error processing email: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def process_emails_by_sender(
        self,
        sender_email: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process emails from a specific sender across all integrations.
        
        Args:
            sender_email: Email address to search for (e.g., "cash@square.com")
            limit: Maximum number of emails per integration
            
        Returns:
            Dictionary with processing results
        """
        results = {
            "processed_emails": 0,
            "new_transactions": 0,
            "errors": 0,
            "transactions": [],
            "duplicate_transactions": [],
            "failed_emails": [],
            "message": "",
            "Erros": []
        }
        
        try:
            logger.info(f"Processing emails from sender: {sender_email}")
            
            # Process emails from all integrations
            for integration, email_msg in self.email_client.process_all_integrations_emails(
                sender_email=sender_email,
                limit=limit
            ):
                results["processed_emails"] += 1
                
                try:
                    transaction = self._process_email(email_msg, integration)
                    
                    if transaction:
                        results["transactions"].append(transaction)
                        results["new_transactions"] += 1
                    else:
                        results["errors"] += 1
                        results["Erros"].append({
                            "email_subject": email_msg.get("subject", ""),
                            "from": email_msg.get("from", ""),
                            "error": "Failed to parse transaction"
                        })
                        
                except Exception as e:
                    results["errors"] += 1
                    error_msg = str(e)
                    results["Erros"].append({
                        "email_subject": email_msg.get("subject", ""),
                        "from": email_msg.get("from", ""),
                        "error": error_msg
                    })
                    logger.error(f"Error processing email: {error_msg}")
            
            # Set success message
            if results["new_transactions"] > 0:
                results["message"] = f"Successfully processed {results['new_transactions']} new transactions"
            else:
                results["message"] = "No new transactions found"
            
            logger.info(f"Processing complete for sender '{sender_email}': {results}")
            
        except Exception as e:
            logger.error(f"Error in process_emails_by_sender: {e}")
            logger.error(traceback.format_exc())
            results["message"] = f"Processing failed: {str(e)}"
        
        return results
    
    def process_emails_by_sender_date_range(
        self,
        sender_email: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Process emails from a specific sender within a date range.
        
        Args:
            sender_email: Email address to search for
            start_date: Start date for search
            end_date: End date for search (optional)
            
        Returns:
            Dictionary with processing results
        """
        results = {
            "processed_emails": 0,
            "new_transactions": 0,
            "errors": 0,
            "transactions": [],
            "duplicate_transactions": [],
            "failed_emails": [],
            "message": "",
            "Erros": []
        }
        
        try:
            logger.info(f"Processing emails from sender: {sender_email}, date range: {start_date} to {end_date}")
            
            # Process emails from all integrations
            for integration, email_msg in self.email_client.process_all_integrations_emails(
                sender_email=sender_email,
                start_date=start_date,
                end_date=end_date
            ):
                results["processed_emails"] += 1
                
                try:
                    transaction = self._process_email(email_msg, integration)
                    
                    if transaction:
                        results["transactions"].append(transaction)
                        results["new_transactions"] += 1
                    else:
                        results["errors"] += 1
                        results["Erros"].append({
                            "email_subject": email_msg.get("subject", ""),
                            "from": email_msg.get("from", ""),
                            "error": "Failed to parse transaction"
                        })
                        
                except Exception as e:
                    results["errors"] += 1
                    error_msg = str(e)
                    results["Erros"].append({
                        "email_subject": email_msg.get("subject", ""),
                        "from": email_msg.get("from", ""),
                        "error": error_msg
                    })
                    logger.error(f"Error processing email: {error_msg}")
            
            # Set success message
            if results["new_transactions"] > 0:
                results["message"] = f"Successfully processed {results['new_transactions']} new transactions"
            else:
                results["message"] = "No new transactions found"
            
            logger.info(f"Processing complete: {results}")
            
        except Exception as e:
            logger.error(f"Error in process_emails_by_sender_date_range: {e}")
            logger.error(traceback.format_exc())
            results["message"] = f"Processing failed: {str(e)}"
        
        return results

