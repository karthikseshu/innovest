"""
Transaction processor for orchestrating email processing workflow.
"""
import logging
import traceback
from typing import Dict, Any, Optional, List
from email.message import Message
from datetime import datetime

from .email_client import EmailClient
from .parser_factory import parser_factory

logger = logging.getLogger(__name__)


class TransactionProcessor:
    """Main processor for handling email transactions."""
    
    def __init__(self):
        self.email_client = EmailClient()
        self.parser_factory = parser_factory

    def _build_failed_entry(self, email_msg: Optional[Message], parser: Optional[Any], error: str, tb: Optional[str] = None) -> Dict[str, Any]:
        """Build a structured failed_emails entry including a safe raw excerpt.

        Returns a dict suitable for adding to `failed_emails` and a compact summary for `Erros`.
        """
        subj = email_msg.get('Subject') if email_msg is not None else 'n/a'
        mid = email_msg.get('Message-ID') if email_msg is not None else 'n/a'
        frm = email_msg.get('From') if email_msg is not None else 'n/a'
        date_hdr = None
        try:
            date_hdr = email_msg.get('Date') if email_msg is not None else None
        except Exception:
            date_hdr = None

        # Try headers string
        headers = None
        try:
            if email_msg is not None:
                headers = '\n'.join([f"{k}: {v}" for k, v in email_msg.items()])
        except Exception:
            try:
                headers = email_msg.as_string() if email_msg is not None else None
            except Exception:
                headers = None

        # Try to get a small body excerpt (decode bytes safely)
        body = None
        try:
            if email_msg is not None:
                payload = email_msg.get_payload(decode=True)
                if isinstance(payload, bytes):
                    try:
                        body = payload.decode(errors='ignore')
                    except Exception:
                        body = None
                elif isinstance(payload, str):
                    body = payload
                else:
                    # leave body None for multipart or complex payloads
                    body = None
        except Exception:
            try:
                pl = email_msg.get_payload()
                if isinstance(pl, str):
                    body = pl
            except Exception:
                body = None

        excerpt = ((headers or '') + '\n\n' + (body or ''))[:4000]

        entry: Dict[str, Any] = {
            'subject': subj,
            'message_id': mid,
            'from': frm,
            'date_header': date_hdr,
            'error': error,
            'parser': getattr(parser, 'name', None),
            'raw_excerpt': excerpt
        }
        if tb:
            entry['traceback'] = tb
        return entry

    def process_emails(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Process unread emails and extract transactions.
        
        Args:
            limit: Maximum number of emails to process
            
        Returns:
            Dictionary with processing results
        """
        results = {
            "processed_emails": 0,
            "new_transactions": 0,
            "errors": 0,
            "transactions": [],
            "failed_emails": [],
            "Erros": []
        }
        
        try:
            with self.email_client:
                # Fetch unread emails
                for email_msg in self.email_client.fetch_unread_emails(limit):
                    results["processed_emails"] += 1
                    
                    try:
                        # Find appropriate parser
                        parser = self.parser_factory.find_parser_for_email(email_msg)
                        if not parser:
                            entry = self._build_failed_entry(email_msg, None, "no parser found")
                            # logger.warning("No parser found for email (subject=%s, message-id=%s)", entry['subject'], entry['message_id'])
                            results["errors"] += 1
                            results.setdefault("failed_emails", []).append(entry)
                            results.setdefault("Erros", []).append({"from": entry['from'], "subject": entry['subject'], "date": entry['date_header'], "error": entry['error']})
                            continue

                        # Parse transaction
                        transaction_data = parser.parse_transaction(email_msg)
                        if not transaction_data:
                            entry = self._build_failed_entry(email_msg, parser, "failed to parse transaction")
                            # logger.warning("Failed to parse transaction from email (subject=%s, message-id=%s)", entry['subject'], entry['message_id'])
                            results["errors"] += 1
                            results.setdefault("failed_emails", []).append(entry)
                            results.setdefault("Erros", []).append({"from": entry['from'], "subject": entry['subject'], "date": entry['date_header'], "error": entry['error']})
                            continue
                        
                        # Instead of storing in DB, normalize and return the parsed transaction
                        normalized = self._normalize_transaction_data(transaction_data, email_msg)
                        results["new_transactions"] += 1
                        results["transactions"].append(normalized)
                        # logger.info(f"Parsed transaction (no-store): {normalized.get('transaction_id')}")
                        
                    except Exception as e:
                        tb = traceback.format_exc()
                        entry = self._build_failed_entry(email_msg, parser if 'parser' in locals() else None, str(e), tb)
                        # logger.exception("Error processing email (subject=%s, message-id=%s): %s", entry['subject'], entry['message_id'], str(e))
                        results["errors"] += 1
                        results.setdefault("failed_emails", []).append(entry)
                        results.setdefault("Erros", []).append({"from": entry['from'], "subject": entry['subject'], "date": entry['date_header'], "error": entry['error']})
                        continue
        
        except Exception as e:
            tb = traceback.format_exc()
            # logger.error(f"Error in email processing workflow: {e}")
            results["errors"] += 1
            results.setdefault("failed_emails", []).append({"error": str(e), "traceback": tb})
            results.setdefault("Erros", []).append({"from": None, "subject": None, "date": None, "error": str(e)})

        # logger.info(f"Processing complete: {results}")
        return results
    
    def process_emails_by_sender(self, sender_email: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Process emails from a specific sender."""
        try:
            # logger.info(f"Processing emails from sender: {sender_email}")
            
            with EmailClient() as email_client:
                emails = list(email_client.search_emails_by_sender(sender_email, limit))
                
            return self._process_email_list(emails, f"sender '{sender_email}'")
            
        except Exception as e:
            tb = traceback.format_exc()
            # logger.error(f"Error processing emails from sender {sender_email}: {e}")
            return {
                "processed_emails": 0,
                "new_transactions": 0,
                "errors": 1,
                "transactions": [],
                "error": str(e),
                "failed_emails": [{"error": str(e), "traceback": tb}],
                "Erros": [{"from": None, "subject": None, "date": None, "error": str(e)}]
            }
    
    def process_emails_by_sender_date_range(self, sender_email: str, start_date: datetime, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Process emails from a specific sender within a date range."""
        try:
            date_range_str = f"from {start_date.date()} to {end_date.date() if end_date else 'now'}"
            logger.info(f"Processing emails from sender: {sender_email} in date range: {date_range_str}")
            
            with EmailClient() as email_client:
                emails = list(email_client.search_emails_by_sender_date_range(sender_email, start_date, end_date))
                
            return self._process_email_list(emails, f"sender '{sender_email}' in date range {date_range_str}")
            
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Error processing emails from sender {sender_email} in date range: {e}")
            return {
                "processed_emails": 0,
                "new_transactions": 0,
                "errors": 1,
                "transactions": [],
                "error": str(e),
                "failed_emails": [{"error": str(e), "traceback": tb}],
                "Erros": [{"from": None, "subject": None, "date": None, "error": str(e)}]
            }
    
    def process_emails_by_content_date_range(self, search_text: str, start_date: datetime, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Process emails containing specific text within a date range."""
        try:
            date_range_str = f"from {start_date.date()} to {end_date.date() if end_date else 'now'}"
            logger.info(f"Processing emails containing '{search_text}' in date range: {date_range_str}")
            
            with EmailClient() as email_client:
                emails = list(email_client.search_emails_by_content_date_range(search_text, start_date, end_date))
                
            return self._process_email_list(emails, f"content '{search_text}' in date range {date_range_str}")
            
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Error processing emails by content '{search_text}' in date range: {e}")
            return {
                "processed_emails": 0,
                "new_transactions": 0,
                "errors": 1,
                "transactions": [],
                "error": str(e),
                "failed_emails": [{"error": str(e), "traceback": tb}],
                "Erros": [{"from": None, "subject": None, "date": None, "error": str(e)}]
            }
    
    def process_emails_by_content(self, search_text: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Process emails containing specific text in subject or body."""
        try:
            logger.info(f"Processing emails containing: '{search_text}'")
            
            with EmailClient() as email_client:
                emails = list(email_client.search_emails_by_content(search_text, limit))
                
            return self._process_email_list(emails, f"content '{search_text}'")
            
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Error processing emails by content '{search_text}': {e}")
            return {
                "processed_emails": 0,
                "new_transactions": 0,
                "errors": 1,
                "transactions": [],
                "error": str(e),
                "failed_emails": [{"error": str(e), "traceback": tb}],
                "Erros": [{"from": None, "subject": None, "date": None, "error": str(e)}]
            }
    
    def process_emails_by_subject(self, search_text: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Process emails with specific text in subject line.
        This is much faster than content search since it only checks subject headers.
        
        Args:
            search_text: Text to search for in email subject
            limit: Maximum number of emails to process
            
        Returns:
            Dictionary with processing results
        """
        results = {
            "processed_emails": 0,
            "new_transactions": 0,
            "errors": 0,
            "transactions": [],
            "failed_emails": [],
            "Erros": []
        }
        
        try:
            with self.email_client:
                for email_msg in self.email_client.search_emails_by_subject(search_text, limit):
                    results["processed_emails"] += 1
                    
                    try:
                        # Find appropriate parser
                        parser = self.parser_factory.find_parser_for_email(email_msg)
                        if not parser:
                            entry = self._build_failed_entry(email_msg, None, "no parser found")
                            # logger.warning("No parser found for email (subject=%s, message-id=%s)", entry['subject'], entry['message_id'])
                            results["errors"] += 1
                            results.setdefault("failed_emails", []).append(entry)
                            results.setdefault("Erros", []).append({"from": entry['from'], "subject": entry['subject'], "date": entry['date_header'], "error": entry['error']})
                            continue

                        # Parse transaction
                        transaction_data = parser.parse_transaction(email_msg)
                        if not transaction_data:
                            entry = self._build_failed_entry(email_msg, parser, "failed to parse transaction")
                            # logger.warning("Failed to parse transaction from email (subject=%s, message-id=%s)", entry['subject'], entry['message_id'])
                            results["errors"] += 1
                            results.setdefault("failed_emails", []).append(entry)
                            results.setdefault("Erros", []).append({"from": entry['from'], "subject": entry['subject'], "date": entry['date_header'], "error": entry['error']})
                            continue

                        # Instead of storing, normalize and return parsed transaction
                        normalized = self._normalize_transaction_data(transaction_data, email_msg)
                        results["new_transactions"] += 1
                        results["transactions"].append(normalized)
                        # logger.info(f"Parsed transaction (no-store): {normalized.get('transaction_id')}")
                        
                    except Exception as e:
                        tb = traceback.format_exc()
                        entry = self._build_failed_entry(email_msg, parser if 'parser' in locals() else None, str(e), tb)
                        # logger.exception("Error processing email (subject=%s, message-id=%s): %s", entry['subject'], entry['message_id'], str(e))
                        results["errors"] += 1
                        results.setdefault("failed_emails", []).append(entry)
                        results.setdefault("Erros", []).append({"from": entry['from'], "subject": entry['subject'], "date": entry['date_header'], "error": entry['error']})
                        continue
        
        except Exception as e:
            tb = traceback.format_exc()
            # logger.error(f"Error in email processing workflow: {e}")
            results["errors"] += 1
            results.setdefault("failed_emails", []).append({"error": str(e), "traceback": tb})
            results.setdefault("Erros", []).append({"from": None, "subject": None, "date": None, "error": str(e)})

        # logger.info(f"Processing complete for subject '{search_text}': {results}")
        return results
    
    def _process_email_list(self, emails: List[Message], source_description: str) -> Dict[str, Any]:
        """Process a list of emails and return results (no DB interactions).
        Dedupe is done per-run using seen transaction_ids."""
        results = {
            "processed_emails": 0,
            "new_transactions": 0,
            "errors": 0,
            "transactions": [],
            "duplicate_transactions": [],
            "message": "",
            "failed_emails": [],
            "Erros": []
        }
        seen_ids = set()
        
        try:
            for email_msg in emails:
                results["processed_emails"] += 1
                
                try:
                    # Find appropriate parser
                    parser = self.parser_factory.find_parser_for_email(email_msg)
                    if not parser:
                        entry = self._build_failed_entry(email_msg, None, "no parser found")
                        logger.warning("No parser found for email (subject=%s, message-id=%s)", entry['subject'], entry['message_id'])
                        results["errors"] += 1
                        results.setdefault("failed_emails", []).append(entry)
                        results.setdefault("Erros", []).append({"from": entry['from'], "subject": entry['subject'], "date": entry['date_header'], "error": entry['error']})
                        continue

                    # Parse transaction
                    transaction_data = parser.parse_transaction(email_msg)
                    if not transaction_data:
                        entry = self._build_failed_entry(email_msg, parser, "failed to parse transaction")
                        logger.warning("Failed to parse transaction from email (subject=%s, message-id=%s)", entry['subject'], entry['message_id'])
                        results["errors"] += 1
                        results.setdefault("failed_emails", []).append(entry)
                        results.setdefault("Erros", []).append({"from": entry['from'], "subject": entry['subject'], "date": entry['date_header'], "error": entry['error']})
                        continue
                    
                    txn_id = transaction_data.get('transaction_id')
                    if txn_id and txn_id in seen_ids:
                        results["duplicate_transactions"].append({
                            "transaction_id": txn_id,
                            "message": f"Transaction {txn_id} already seen in this run"
                        })
                        logger.info(f"Transaction already seen in run: {txn_id}")
                        continue
                    
                    normalized = self._normalize_transaction_data(transaction_data, email_msg)
                    results["new_transactions"] += 1
                    results["transactions"].append(normalized)
                    if txn_id:
                        seen_ids.add(txn_id)
                    logger.info(f"Parsed transaction (no-store): {txn_id}")
                
                except Exception as e:
                    tb = traceback.format_exc()
                    entry = self._build_failed_entry(email_msg, parser if 'parser' in locals() else None, str(e), tb)
                    logger.exception("Error processing email (subject=%s, message-id=%s): %s",
                        entry['subject'],
                        entry['message_id'],
                        str(e))
                    results["errors"] += 1
                    results.setdefault("failed_emails", []).append(entry)
                    results.setdefault("Erros", []).append({"from": entry['from'], "subject": entry['subject'], "date": entry['date_header'], "error": entry['error']})
                    continue
            
            # Set appropriate message
            if results["new_transactions"] > 0 and results["duplicate_transactions"]:
                results["message"] = f"Found {results['new_transactions']} new transactions and {len(results['duplicate_transactions'])} duplicate transactions"
            elif results["new_transactions"] > 0:
                results["message"] = f"Successfully processed {results['new_transactions']} new transactions"
            elif results["duplicate_transactions"]:
                results["message"] = f"All {len(results['duplicate_transactions'])} transactions already exist in database"
            else:
                results["message"] = "No transactions found or processed"
            
            logger.info(f"Processing complete for {source_description}: {results}")
            return results
            
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Error in email processing workflow: {e}")
            results["errors"] += 1
            results["message"] = f"Error processing emails: {str(e)}"
            results.setdefault("failed_emails", []).append({"error": str(e), "traceback": tb})
            results.setdefault("Erros", []).append({"from": None, "subject": None, "date": None, "error": str(e)})
            return results
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get email processing statistics."""
        try:
            with self.email_client:
                mailbox_info = self.email_client.get_mailbox_info()
                if mailbox_info:
                    return {
                        "mailbox_info": mailbox_info,
                        "supported_parsers": self.parser_factory.list_supported_providers(),
                        "total_parsers": len(self.parser_factory.get_all_parsers())
                    }
                else:
                    return {
                        "error": "Could not retrieve mailbox information",
                        "supported_parsers": self.parser_factory.list_supported_providers(),
                        "total_parsers": len(self.parser_factory.get_all_parsers())
                    }
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {
                "error": str(e),
                "supported_parsers": self.parser_factory.list_supported_providers(),
                "total_parsers": len(self.parser_factory.get_all_parsers())
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test email connection only (DB removed)."""
        results = {
            "email_connection": False,
            "errors": []
        }
        
        # Test email connection
        try:
            with self.email_client:
                if self.email_client.is_connected():
                    results["email_connection"] = True
                else:
                    results["errors"].append("Failed to connect to email server")
        except Exception as e:
            results["errors"].append(f"Email connection error: {e}")
        
        return results

    def _normalize_transaction_data(self, transaction_data: Dict[str, Any], email_msg: Optional[Message] = None) -> Dict[str, Any]:
        """
        Normalize parsed transaction data and ensure email_date contains full datetime (with time).
        This returns a dict suitable for API responses.

        If the parser returned only a date (no time), attempt to extract the full datetime from
        the raw email headers (e.g. Date: or Received: headers) present in `raw_email_data` or from
        the provided email.message.Message (`email_msg`).

        Args:
            transaction_data: parsed transaction dict from parser
            email_msg: optional email.message.Message object; used to extract headers if raw_email_data missing
        """
        # Local imports
        try:
            from dateutil import parser as _date_parser
        except Exception:
            _date_parser = None
        import re
        from typing import Optional, Tuple, Any

        def _extract_datetime_from_raw_email(raw: Any) -> Tuple[Optional[datetime], Optional[str]]:
            """Try to extract a datetime from raw email headers (Date: or Received:).
            Returns (datetime, matched_header_snippet) or (None, None)."""
            if not raw:
                return None, None
            raw_str = str(raw)

            # 1) Prefer the Date: header
            m = re.search(r'(?mi)^\s*Date:\s*(.+)$', raw_str)
            if m:
                date_val = m.group(1).strip()
                try:
                    dt = _date_parser.parse(date_val) if _date_parser else datetime.fromisoformat(date_val)
                    return dt, m.group(0).strip()
                except Exception:
                    pass

            # 2) Look for Received: ...; <timestamp> (last Received header often has the original timestamp)
            received_matches = re.findall(r'(?mi)^Received:.*?;\s*(.+)$', raw_str)
            if received_matches:
                for date_val in reversed(received_matches):
                    date_val = date_val.strip()
                    try:
                        dt = _date_parser.parse(date_val) if _date_parser else datetime.fromisoformat(date_val)
                        # find the full header line that contained this date for debugging
                        header_line_search = re.search(re.escape(date_val) + r".*", raw_str)
                        header_snippet = header_line_search.group(0).strip() if header_line_search else date_val
                        return dt, header_snippet
                    except Exception:
                        continue

            # 3) Try to find any RFC-like timestamp anywhere in the headers
            rfc_like = re.search(r'([A-Za-z]{3},\s*\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+[+-]\d{4})', raw_str)
            if rfc_like:
                try:
                    dt = _date_parser.parse(rfc_like.group(1)) if _date_parser else datetime.fromisoformat(rfc_like.group(1))
                    return dt, rfc_like.group(0).strip()
                except Exception:
                    pass

            return None, None

        # If raw headers not present in transaction_data, but we have email_msg, extract headers string
        if not transaction_data.get('raw_email_data') and email_msg is not None:
            try:
                headers = '\n'.join([f"{k}: {v}" for k, v in email_msg.items()])
                transaction_data['raw_email_data'] = headers
            except Exception:
                try:
                    transaction_data['raw_email_data'] = email_msg.as_string()
                except Exception:
                    transaction_data['raw_email_data'] = None

        model_data: Dict[str, Any] = {}

        model_data['transaction_id'] = transaction_data.get('transaction_id')
        model_data['sender'] = transaction_data.get('sender') or transaction_data.get('paid_by')
        model_data['recipient'] = transaction_data.get('recipient') or transaction_data.get('paid_to')
        model_data['amount'] = transaction_data.get('amount')
        model_data['currency'] = transaction_data.get('currency', 'USD')
        model_data['transaction_type'] = transaction_data.get('transaction_type', 'transfer')

        payment_status = transaction_data.get('status') or transaction_data.get('payment_status')
        if payment_status is not None:
            try:
                model_data['status'] = str(payment_status).lower()
            except Exception:
                model_data['status'] = payment_status

        model_data['description'] = transaction_data.get('description')
        model_data['email_subject'] = transaction_data.get('email_subject') or transaction_data.get('description')

        # Parse transaction_date preserving time when available
        txn_date = transaction_data.get('transaction_date') or transaction_data.get('email_date')
        email_date = None
        raw_used_for_parsing = False

        if txn_date:
            if isinstance(txn_date, datetime):
                email_date = txn_date
            else:
                # try dateutil then common formats
                if _date_parser:
                    try:
                        email_date = _date_parser.parse(str(txn_date))
                    except Exception:
                        email_date = None
                if email_date is None:
                    try:
                        # fallback common iso or mm/dd/YYYY with optional time
                        email_date = datetime.fromisoformat(str(txn_date))
                    except Exception:
                        try:
                            email_date = datetime.strptime(str(txn_date), '%m/%d/%Y %H:%M:%S')
                        except Exception:
                            try:
                                email_date = datetime.strptime(str(txn_date), '%m/%d/%Y')
                            except Exception:
                                email_date = None

        # If still none and parser provided raw email_date, attempt parse
        if not email_date and transaction_data.get('email_date'):
            try:
                if _date_parser:
                    email_date = _date_parser.parse(str(transaction_data.get('email_date')))
                else:
                    email_date = datetime.fromisoformat(str(transaction_data.get('email_date')))
            except Exception:
                email_date = None

        # Prefer using datetime found in headers when it includes time information.
        extracted, extracted_header_snippet = None, None
        try:
            # Try raw_email_data first
            raw_email = transaction_data.get('raw_email_data')
            extracted, extracted_header_snippet = _extract_datetime_from_raw_email(raw_email)

            # If not found, and we have email_msg, build headers string and try again
            if not extracted and email_msg is not None:
                try:
                    headers = '\n'.join([f"{k}: {v}" for k, v in email_msg.items()])
                except Exception:
                    try:
                        headers = email_msg.as_string()
                    except Exception:
                        headers = None
                if headers:
                    extracted, extracted_header_snippet = _extract_datetime_from_raw_email(headers)
        except Exception:
            extracted, extracted_header_snippet = None, None

        # Choose extracted header datetime when appropriate:
        # - if parser provided no date, use extracted
        # - if parser provided a date but it appears date-only (midnight), prefer extracted
        if extracted:
            try:
                prefer_header = False
                if not email_date:
                    prefer_header = True
                else:
                    if isinstance(email_date, datetime) and email_date.hour == 0 and email_date.minute == 0 and email_date.second == 0:
                        prefer_header = True

                if prefer_header:
                    email_date = extracted
                    raw_used_for_parsing = True
                else:
                    # keep parser date
                    raw_used_for_parsing = False
            except Exception:
                # fallback: use extracted
                email_date = extracted
                raw_used_for_parsing = True
        else:
            extracted_header_snippet = None

        # Store ISO formatted datetime string with timezone info if present
        if email_date:
            try:
                model_data['email_date'] = email_date.isoformat()
            except Exception:
                model_data['email_date'] = str(email_date)
        else:
            model_data['email_date'] = None

        # Record source of email_date for debugging: 'parsed' when from parser, 'raw_headers' when extracted
        if email_date:
            if raw_used_for_parsing:
                model_data['email_date_source'] = 'raw_headers'
                if extracted_header_snippet:
                    model_data['email_date_header_match'] = extracted_header_snippet
            else:
                model_data['email_date_source'] = 'parsed'
                model_data['email_date_header_match'] = None
        else:
            model_data['email_date_source'] = None
            model_data['email_date_header_match'] = None

        model_data['source_provider'] = transaction_data.get('source_provider') or 'unknown'
        model_data['raw_email_data'] = transaction_data.get('raw_email_data')
        model_data['deposited_to'] = transaction_data.get('deposited_to')
        model_data['cashapp_transaction_number'] = transaction_data.get('transaction_number') or transaction_data.get('cashapp_transaction_number')

        # Keep original parsed transaction_date field as well (if present)
        if transaction_data.get('transaction_date'):
            model_data['transaction_date'] = transaction_data.get('transaction_date')

        # Optionally note that datetime was extracted from raw headers (for debugging)
        if raw_used_for_parsing:
            model_data['email_date_source'] = 'raw_headers'

        return model_data
