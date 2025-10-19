"""
Cash App email parser for extracting transaction information.
"""
import re
from typing import Dict, Optional, Any
from email.message import Message
from datetime import datetime

from .base_parser import BaseParser


class CashAppParser(BaseParser):
    """Parser for Cash App transaction emails."""
    
    def __init__(self):
        super().__init__("cashapp")
        
        # Cash App specific patterns
        self.amount_patterns = [
            r"\$([0-9,]+\.?[0-9]*)",  # $123.45 or $1,234.56
            r"([0-9,]+\.?[0-9]*)\s*USD",  # 123.45 USD
        ]
        
        self.sender_patterns = [
            r"from\s+([A-Za-z\s\.']+(?:\s+[A-Za-z']+)*)",  # "from John Doe"
            r"sent\s+by\s+([A-Za-z\s\.']+(?:\s+[A-Za-z']+)*)",  # "sent by John Doe"
            r"([A-Za-z\s\.']+(?:\s+[A-Za-z']+)*)\s+sent\s+you",  # "John Doe sent you"
            r"Sender:\s*([A-Za-z\s\.']+(?:\s+[A-Za-z']+)*)",  # "Sender: John Doe"
        ]
        
        self.recipient_patterns = [
            r"to\s+([A-Za-z\s']+(?:\s+[A-Za-z']+)*)",  # "to Jane Doe"
            r"sent\s+to\s+([A-Za-z\s']+(?:\s+[A-Za-z']+)*)",  # "sent to Jane Doe"
            r"Recipient:\s*([A-Za-z\s']+(?:\s+[A-Za-z']+)*)",  # "Recipient: Jane Doe"
        ]
        
        self.transaction_type_patterns = [
            (r"payment\s+request", "request"),
            (r"requested\s+payment", "request"),
            (r"sent\s+you\s+money", "received"),
            (r"you\s+sent", "sent"),
            (r"payment\s+received", "received"),
        ]
    
    def can_parse(self, email_message: Message) -> bool:
        """Check if this is a Cash App email."""
        from_address = email_message.get("from", "").lower()
        subject = email_message.get("subject", "").lower()
        body = self.extract_email_body(email_message).lower()
        
        # Check for Cash App email addresses
        cashapp_indicators = [
            "cash@square.com",
            "noreply@cash.app",
            "cash.app",
            "square cash"
        ]
        
        # Check for Cash App in subject, from address, or body
        for indicator in cashapp_indicators:
            if indicator in from_address or indicator in subject or indicator in body:
                # Additional check: filter out promotional emails
                promotional_keywords = [
                    "get up to", "referral", "bonus", "offer", "sweepstakes", 
                    "enter to win", "limited time", "promotion", "invite friends"
                ]
                
                # If it's a promotional email, don't parse it as a transaction
                for keyword in promotional_keywords:
                    if keyword in subject.lower() or keyword in body.lower():
                        return False
                
                return True
        
        # Check for Cash App specific subject patterns
        subject_patterns = [
            r"cash\s+app",
            r"payment\s+(?:received|sent|request)",
            r"\$\d+",
            r"sent\s+you\s+\$",
            r"you\s+sent\s+\$",
        ]
        
        for pattern in subject_patterns:
            if re.search(pattern, subject, re.IGNORECASE):
                return True
        
        # Check for Cash App specific body patterns (for forwarded emails)
        body_patterns = [
            r"cash\s+app\s+logo",
            r"transaction\s+details",
            r"payment\s+has\s+completed",
            r"transaction\s+number",
            r"#d-[a-z0-9]+",  # Cash App transaction ID format
        ]
        
        for pattern in body_patterns:
            if re.search(pattern, body, re.IGNORECASE):
                return True
        
        return False
    
    def _clean_name(self, name: str) -> str:
        """Clean up extracted names by removing unwanted content."""
        if not name:
            return name

        # Remove leading/trailing whitespace
        name = name.strip()

        # Remove HTML tags if any
        name = re.sub(r'<[^>]+>', '', name).strip()

        # Remove everything after newline/carriage return
        name = re.sub(r'\r?\n.*$', '', name).strip()

        # Remove any trailing punctuation or extra spaces (but preserve periods and apostrophes inside names)
        name = re.sub(r'[\s\-]{2,}', ' ', name).strip()
        name = re.sub(r'[\t\r\n]+', ' ', name).strip()

        # Remove common footer words that sometimes appear in forwarded content
        name = re.sub(r'\b(Privacy Policy|Terms|Support|https?://\S+)\b', '', name, flags=re.IGNORECASE).strip()

        # Final cleanup - remove unwanted characters but allow letters, numbers, spaces, dots, apostrophes, hyphens
        name = re.sub(r"[^\w\s\.'-]", ' ', name).strip()

        # Collapse multiple spaces
        name = re.sub(r'\s+', ' ', name).strip()

        return name

    def _extract_payment_between(self, content: str) -> Optional[Dict[str, str]]:
        """Extract Sender and Recipient from a 'Payment between' block if present."""
        # Allow matching across newlines and tolerate extra spacing/lines
        match = re.search(
            r"Payment\s+between[:\s]*.*?Recipient[:\s]*([^\n\r]+).*?Sender[:\s]*([^\n\r]+)",
            content, re.IGNORECASE | re.DOTALL
        )
        if match:
            recipient = self._clean_name(match.group(1).strip())
            sender = self._clean_name(match.group(2).strip())
            return {"recipient": recipient, "sender": sender}
        return None

    def _extract_account_owner(self, body: str, subject: str) -> Optional[str]:
        """Try to find the account owner's display name near the top of the email body.
        Looks for the first short line with 2-4 capitalized words (e.g. 'Emmanuel Pagan Rosario')."""
        content = body + "\n" + subject
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        for line in lines[:10]:
            low = line.lower()
            if any(x in low for x in ['http://', 'https://', 'cash.app', 'to report a problem', 'transaction details', 'payment between', 'today', 'yesterday']):
                continue
            # Accept lines with 2-4 words that look like names (require each word be at least 2 letters)
            if re.match(r"^[A-Za-z][a-zA-Z\.'-]{1,}(?:\s+[A-Za-z][a-zA-Z\.'-]{1,}){1,3}$", line):
                candidate = self._clean_name(line)
                # reject if candidate looks like an email or single letter
                if '@' in candidate or len(candidate) <= 1:
                    continue
                return candidate
        return None

    def parse_transaction(self, email_message: Message) -> Optional[Dict[str, Any]]:
        """Parse Cash App email and extract transaction information."""
        try:
            subject = email_message.get("subject", "")
            body = self.extract_email_body(email_message)

            self.logger.info(f"Parsing Cash App email: {subject}")
            self.logger.info(f"Email body length: {len(body)}")
            self.logger.info(f"Email body preview: {body[:500]}...")
            
            # Debug: Check if we can find transaction numbers in the raw body
            import re
            txn_matches = re.findall(r'#D-[A-Za-z0-9-]+', body)
            self.logger.info(f"Transaction number matches in body: {txn_matches}")

            content = body + " " + subject

            # If this email was forwarded, prefer the original Cash App section for parsing
            # (many Gmail forwards include both the outer wrapper and the original message).
            parsing_body = body
            try:
                m = re.search(r"(From:\s*Cash App\s*<cash@square\.com>|From:\s*cash@square\.com|[-]{3,}\s*Forwarded message|Original Message)", body, re.IGNORECASE)
                if m:
                    # start parsing from the original Cash App section to avoid picking values from the wrapper
                    parsing_body = body[m.start():]
                    self.logger.info("Detected forwarded message; using inner Cash App section for parsing")
            except Exception:
                pass

            # provenance tracking
            sender_source = 'unknown'
            recipient_source = 'unknown'
            txn_source = 'unknown'

            # Extract basic transaction information
            amount = self._extract_amount(body, subject)
            if not amount:
                self.logger.warning("Could not extract amount from email")
                return None

            # First try to extract 'payment between' block which reliably contains sender/recipient
            pb = self._extract_payment_between(content)
            if pb:
                sender_override = pb.get('sender')
                recipient_override = pb.get('recipient')
            else:
                sender_override = None
                recipient_override = None

            # Extract sender and recipient (prefer parsing_body which may be the inner original message)
            sender = self._extract_sender(parsing_body, subject)
            sender_source = 'body' if sender else 'unknown'
            recipient = self._extract_recipient(parsing_body, subject)
            recipient_source = 'body' if recipient else 'unknown'

            # Prefer values from 'Payment between' block if present (more authoritative)
            if sender_override:
                sender = sender_override
                sender_source = 'payment_between'
            if recipient_override:
                recipient = recipient_override
                recipient_source = 'payment_between'

            # Normalize obvious placeholders
            if sender and sender.lower() in ['cash app', 'cashapp', 'noreply', 'noreply@cash.app', 'unknown']:
                # if we detected an account owner, map the placeholder to that owner
                account_owner = self._extract_account_owner(body, subject)
                if not account_owner:
                    account_owner = self._parse_display_name_from_header(email_message.get('from') or '')
                if account_owner and self._is_valid_name(account_owner):
                    sender = account_owner
                    sender_source = 'mapped_account_owner'
                else:
                    sender = None
                    sender_source = 'unknown'
            if recipient and isinstance(recipient, str) and recipient.lower() in ['cash app', 'cashapp', 'noreply', 'noreply@cash.app', 'unknown']:
                account_owner = self._extract_account_owner(body, subject)
                if not account_owner:
                    account_owner = self._parse_display_name_from_header(email_message.get('from') or '')
                if account_owner and self._is_valid_name(account_owner):
                    recipient = account_owner
                    recipient_source = 'mapped_account_owner'
                else:
                    recipient = None
                    recipient_source = 'unknown'

            # If sender or recipient equals literal 'You', replace with account owner display name when available
            account_owner = self._extract_account_owner(body, subject)
            # If we couldn't detect account owner in the body/subject, try the From header display name
            if not account_owner:
                account_owner = self._parse_display_name_from_header(email_message.get('from') or '')

            # Reject vendor/service-like display names as account owner (avoid mapping to 'Cash App', 'noreply', etc.)
            if account_owner:
                low_owner = account_owner.lower()
                vendor_tokens = ['cash', 'cash app', 'cashapp', 'square', 'noreply', 'support', 'receipt', 'help', 'cash.me']
                if any(tok in low_owner for tok in vendor_tokens):
                    self.logger.info(f"Detected vendor-like account_owner '{account_owner}', ignoring as account owner")
                    account_owner = None

            if sender and sender.strip().lower() == 'you' and account_owner:
                sender = account_owner
                sender_source = 'account_owner'
            if recipient and isinstance(recipient, str) and recipient.strip().lower() == 'you' and account_owner:
                recipient = account_owner
                recipient_source = 'account_owner'

            # As an extra fallback, if sender/recipient still literal 'You', try From/To headers individually
            if sender and sender.strip().lower() == 'you':
                parsed = self._parse_display_name_from_header(email_message.get('from') or '')
                if parsed:
                    sender = parsed
                    sender_source = 'header'
            if recipient and isinstance(recipient, str) and recipient.strip().lower() == 'you':
                parsed_to = self._parse_display_name_from_header(email_message.get('to') or '')
                if parsed_to:
                    recipient = parsed_to
                    recipient_source = 'header'

            # If sender still missing, try to get from 'From:' header or subject
            if not sender:
                sender_candidate = self._parse_display_name_from_header(email_message.get('from') or '')
                if sender_candidate:
                    sender = sender_candidate
                    sender_source = 'header'

            # If recipient still missing, try 'To:' header
            if not recipient:
                recipient_candidate = self._parse_display_name_from_header(email_message.get('to') or '')
                if recipient_candidate:
                    recipient = recipient_candidate
                    recipient_source = 'header'

            if not sender or not recipient:
                self.logger.warning("Could not extract sender or recipient from email")
                return None

            self.logger.info(f"Extracted sender: {sender} (source={sender_source}), recipient: {recipient} (source={recipient_source})")

            # Extract additional details from the (preferentially) inner parsing_body
            deposited_to = self._extract_deposited_to(parsing_body, subject)
            transaction_number = self._extract_transaction_number(parsing_body, subject)
            self.logger.info(f"Extracted transaction number: '{transaction_number}'")

            # If we couldn't find a transaction number (or sender resolved to 'You'), try HTML part fallback
            if (not transaction_number) or (sender and sender.strip().lower() == 'you'):
                try:
                    for part in email_message.walk():
                        if part.get_content_type() == 'text/html':
                            try:
                                html = part.get_content()
                            except Exception:
                                # fallback to payload decoding
                                html = part.get_payload(decode=True).decode(errors='ignore') if part.get_payload(decode=True) else ''

                            # convert minimal HTML to text for regex matching
                            html_text = re.sub(r'<[^>]+>', '\n', html)

                            # Try to extract a Payment between block from HTML and prefer it if valid
                            try:
                                # First, try the existing Payment between extraction on cleaned text
                                pb_html = self._extract_payment_between(html_text)
                                if pb_html:
                                    candidate_recipient = pb_html.get('recipient')
                                    candidate_sender = pb_html.get('sender')
                                    vendor_tokens = ['cash', 'cash app', 'cashapp', 'square', 'noreply', 'support', 'receipt', 'help', 'cash.me']
                                    if candidate_recipient and self._is_valid_name(candidate_recipient) and not any(tok in candidate_recipient.lower() for tok in vendor_tokens):
                                        recipient = candidate_recipient
                                        recipient_source = 'html:payment_between'
                                    if candidate_sender and self._is_valid_name(candidate_sender) and not any(tok in candidate_sender.lower() for tok in vendor_tokens):
                                        sender = candidate_sender
                                        sender_source = 'html:payment_between'
                                else:
                                    # Try HTML-aware regex directly on raw html to catch patterns like:
                                    # Recipient: Blockchain Realty<br>                             Sender: Barbara Amador
                                    html_pair_match = re.search(r"Recipient[:\s]*([^<\n\r]+?)\s*<br[^>]*>\s*Sender[:\s]*([^<\n\r]+?)",
                                                               html, re.IGNORECASE | re.DOTALL)
                                    if html_pair_match:
                                        candidate_recipient = html_pair_match.group(1).strip()
                                        candidate_sender = html_pair_match.group(2).strip()
                                        candidate_recipient = self._clean_name(candidate_recipient)
                                        candidate_sender = self._clean_name(candidate_sender)
                                        vendor_tokens = ['cash', 'cash app', 'cashapp', 'square', 'noreply', 'support', 'receipt', 'help', 'cash.me']
                                        if candidate_recipient and self._is_valid_name(candidate_recipient) and not any(tok in candidate_recipient.lower() for tok in vendor_tokens):
                                            recipient = candidate_recipient
                                            recipient_source = 'html:payment_between_raw'
                                        if candidate_sender and self._is_valid_name(candidate_sender) and not any(tok in candidate_sender.lower() for tok in vendor_tokens):
                                            sender = candidate_sender
                                            sender_source = 'html:payment_between_raw'
                            except Exception:
                                pass

                            # try to extract transaction number and sender/recipient from html_text
                            if not transaction_number:
                                txn_from_html = self._extract_transaction_number(html_text, subject)
                                if txn_from_html:
                                    transaction_number = txn_from_html
                                    txn_source = 'html'
                            # if sender is literal 'You', try to extract from html
                            if sender and sender.strip().lower() == 'you':
                                s_from_html = self._extract_sender(html_text, subject)
                                if s_from_html and s_from_html.lower() not in ['you', 'unknown', 'cash app', 'cashapp', 'noreply']:
                                    sender = s_from_html
                                    sender_source = 'html'
                                    # also update paid_by field later
                            # if recipient is literal 'You', try html
                            if recipient and isinstance(recipient, str) and recipient.strip().lower() == 'you':
                                r_from_html = self._extract_recipient(html_text, subject)
                                if r_from_html and r_from_html.lower() not in ['you', 'unknown', 'cash app', 'cashapp', 'noreply']:
                                    recipient = r_from_html
                                    recipient_source = 'html'

                            # if both found, break early
                            if transaction_number and (sender and sender.strip().lower() != 'you') and (not (recipient and recipient.strip().lower() == 'you')):
                                break
                except Exception:
                    pass

            # Enforce: transaction_number MUST be present in email — do not generate one
            if not transaction_number:
                self.logger.warning("No explicit transaction number found in email after HTML fallback; aborting parse (transaction_number required)")
                return None

            # infer transaction number provenance
            if transaction_number:
                if re.match(r'^#D[-A-Za-z0-9]+', transaction_number, re.IGNORECASE):
                    txn_source = 'label:#D'
                elif txn_source != 'html':
                    txn_source = 'body-extracted'

            transaction_date = self._extract_transaction_date(parsing_body, subject)
            payment_status = self._extract_payment_status(parsing_body, subject)

            # Determine transaction type
            transaction_type = self._determine_transaction_type(body, subject)

            # Use transaction_number as transaction_id (no auto-generation)
            transaction_id = transaction_number

            # Build transaction data matching the API response format
            transaction_data = {
                'transaction_id': transaction_id,
                'amount': amount,  # This will be used for both validation and storage
                'amount_paid': amount,
                'currency': 'USD',
                'transaction_type': transaction_type.title() if transaction_type else 'Cash',
                'payment_status': payment_status.title() if payment_status else 'Completed',
                'paid_by': sender,
                'paid_to': recipient,
                'sender': sender,  # Required field for validation
                'deposited_to': deposited_to or 'Cash balance',
                'transaction_number': transaction_number,
                'transaction_date': datetime.strftime(transaction_date if transaction_date else self._extract_email_date(email_message), '%Y-%m-%dT00:00:00'),  # ISO-like date with midnight
                'source_provider': 'cashapp',
                'raw_email_data': body,
                'description': subject  # Use email subject as description
            }

            # Log provenance for debugging
            self.logger.info(f"Provenance -> txn_number: {transaction_data.get('transaction_number')} (source={txn_source}), sender: {sender} (source={sender_source}), recipient: {recipient} (source={recipient_source})")

            self.logger.info(f"Built transaction data: {transaction_data}")

            # Validate the data
            if not self.validate_transaction_data(transaction_data):
                self.logger.warning("Transaction data validation failed")
                return None

            self.logger.info("Transaction parsing successful")
            return transaction_data

        except Exception as e:
            self.logger.error(f"Error parsing Cash App email: {e}")
            return None
    
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
    
    def _extract_sender(self, body: str, subject: str) -> str:
        """Extract sender information from email content."""
        content = body + " " + subject

        # Always prioritize the 'Payment between' section if present
        payment_between_match = re.search(
            r"Payment\s+between[:\s]*\n?.*?Recipient[:\s]*([^\n\r]+?)\s*[\n\r]+.*?Sender[:\s]*([^\n\r]+?)",
            content, re.IGNORECASE | re.DOTALL
        )
        if payment_between_match:
            sender = payment_between_match.group(2).strip()
            self.logger.info(f"Found sender from Payment between section: '{sender}'")
            return self._clean_name(sender)

        # Handle phrasing like "You were sent $350 by Sarah Olivieri." (capture the 'by' name)
        # Use non-greedy capture and stop before common trailing phrases (period, comma, or 'To view')
        you_were_sent_by_match = re.search(
            r"You\s+were\s+sent\s+\$[0-9,]+(?:\.[0-9]+)?\s+by\s+([A-Za-z\s\.'-]+?)(?=(?:\.|,|\s+To view|\s+to view|$))",
            content, re.IGNORECASE
        )
        if you_were_sent_by_match:
            sender = you_were_sent_by_match.group(1).strip()
            # Remove trailing receipt-related phrases that sometimes follow the name
            sender = re.sub(r"\s*(?:\.\s*)?(?:To view your receipt.*|to view your receipt.*|View your receipt.*)$", '', sender, flags=re.IGNORECASE).strip()
            sender = re.sub(r'^(?:receipt\s*)', '', sender, flags=re.IGNORECASE).strip()
            sender = self._clean_name(sender)
            # Guard against accidental single-letter captures (e.g. 'B')
            if sender and len(sender) > 1:
                self.logger.info(f"Found sender from 'You were sent ... by' pattern: '{sender}'")
                return sender

        # Look for exact patterns from the email template
        exact_patterns = [
            r"Sender:\s*([^\n\r]+)",  # "Sender: Blockchain Realty"
            r"Paid\s+by:\s*([^\n\r]+)",  # "Paid by: Blockchain Realty"
        ]
        for pattern in exact_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                sender = match.group(1).strip()
                self.logger.info(f"Found sender with exact pattern '{pattern}': '{sender}'")
                # strip accidental leading 'receipt' token when present (appears in some templates)
                sender = re.sub(r'^(?:receipt\s*)', '', sender, flags=re.IGNORECASE).strip()
                sender = self._clean_name(sender)
                if sender and len(sender) > 1:
                    return sender

        # For simple text emails, look for 'You sent $X to Y' pattern – in that case the sender is the account owner ("You").
        you_sent_match = re.search(r"You\s+sent\s+\$[0-9,]+(?:\.[0-9]+)?", content, re.IGNORECASE)
        if you_sent_match:
            # Try to extract account owner from other parts (Payment between, 'From:', etc.)
            from_match = re.search(r"From[:\s]+([^<\n\r]+)", content, re.IGNORECASE)
            if from_match:
                candidate = from_match.group(1).strip()
                candidate = self._clean_name(candidate)
                if candidate and candidate.lower() not in ["cash app", "noreply", "noreply@cash.app"]:
                    return candidate

            # Fallback to returning 'You' to indicate account owner
            self.logger.info("Found 'You sent' pattern, using 'You' as sender (account owner)")
            return "You"

        # Look for specific Cash App patterns first (more restrictive)
        cashapp_patterns = [
            r"([A-Za-z\s\.'-]+(?:\s+[A-Za-z\.'-]+)*)\s+sent\s+you\s+\$",  # "Ashley Vegas sent you $"
            r"([A-Za-z\s\.'-]+(?:\s+[A-Za-z\.'-]+)*)\s+paid\s+you\s+\$",  # "Barbara Amador paid you $"
            r"([A-Za-z\s\.'-]+(?:\s+[A-Za-z\.'-]+)*)\s+requested\s+payment",
            r"Sender[:\s]+([A-Za-z\s\.'-]+(?:\s+[A-Za-z\.'-]+)*)",  # "Sender: Ashley Vegas's"
            r"From[:\s]+([A-Za-z\s\.'-]+(?:\s+[A-Za-z\.'-]+)*)",  # "From: Ashley Vegas's"
        ]
        for pattern in cashapp_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                sender = match.group(1).strip()
                sender = self._clean_name(sender)
                # reject obviously short captures
                if sender and len(sender) > 2 and len(sender) < 200:
                    self.logger.info(f"Found sender with pattern '{pattern}': '{sender}'")
                    return sender

        # Fallback to general sender patterns
        for pattern in self.sender_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                sender = match.group(1).strip()
                sender = self._clean_name(sender)
                if (sender and sender.lower() not in ["you", "your", "me"] and len(sender) > 2 and len(sender) < 200):
                    return sender

        return "Unknown"

    def _extract_recipient(self, body: str, subject: str) -> Optional[str]:
        """Extract recipient information from email content."""
        content = body + " " + subject

        self.logger.info(f"Searching for recipient in content: {content[:500]}...")

        # Always prioritize the 'Payment between' section if present
        payment_between_match = re.search(
            r"Payment\s+between[:\s]*\n?.*?Recipient[:\s]*([^\n\r]+?)\s*[\n\r]+.*?Sender[:\s]*([^\n\r]+?)",
            content, re.IGNORECASE | re.DOTALL
        )
        if payment_between_match:
            recipient = payment_between_match.group(1).strip()
            self.logger.info(f"Found recipient from Payment between section: '{recipient}'")
            return self._clean_name(recipient)

        # Look for 'You sent $X to <Recipient>' and capture everything up to ' for ' or newline or end
        you_sent_match = re.search(r"You\s+sent\s+\$[0-9,]+(?:\.[0-9]+)?\s+to\s+([^\n\r]+?)(?:\s+for|\s*$|\s*\n)", content, re.IGNORECASE)
        if you_sent_match:
            recipient = you_sent_match.group(1).strip()
            self.logger.info(f"Found recipient from 'You sent' pattern: '{recipient}'")
            recipient = self._clean_name(recipient)
            if recipient:
                return recipient

        # For 'sent you' emails, the recipient is 'You'
        sent_you_match = re.search(r"([^\n\r]+?)\s+sent\s+you\s+\$", content, re.IGNORECASE)
        if sent_you_match:
            self.logger.info("Found 'sent you' pattern, using 'You' as recipient")
            return "You"

        # Look for specific Cash App transaction patterns first (more permissive)
        cashapp_patterns = [
            r"Recipient[:\s]*([^\n\r]+)",  # "Recipient: Blockchain Realty"
            r"Paid\s+to[:\s]*([^\n\r]+)",  # "Paid to: Blockchain Realty"
            r"([^\n\r]+?)\s+received\s+\$",  # "Blockchain Realty received $"
            r"sent\s+to\s+([^\n\r]+)",  # "sent to Blockchain Realty"
            r"paid\s+([^\n\r]+)",  # "paid Blockchain Realty"
        ]
        for pattern in cashapp_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                recipient = match.group(1).strip()
                self.logger.info(f"Found recipient with pattern '{pattern}': '{recipient}'")
                if recipient and len(recipient) > 2:
                    # Remove trailing receipt phrases that sometimes leak into captures
                    recipient = re.sub(r"\s*(?:\.\s*)?(?:To view your receipt.*|to view your receipt.*|View your receipt.*)$", '', recipient, flags=re.IGNORECASE).strip()
                    recipient = self._clean_name(recipient)
                    self.logger.info(f"Cleaned recipient: '{recipient}'")
                    if recipient.lower() not in ["you", "your", "me", "cash", "balance", "view", "receipt", "visit", "url"]:
                        return recipient

        # Fallback to general recipient patterns
        for pattern in self.recipient_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                recipient = match.group(1).strip()
                if recipient and recipient.lower() not in ["you", "your", "me"] and len(recipient) > 2:
                    recipient = re.sub(r"\s*(?:\.\s*)?(?:To view your receipt.*|to view your receipt.*|View your receipt.*)$", '', recipient, flags=re.IGNORECASE).strip()
                    recipient = self._clean_name(recipient)
                    return recipient

        return None
    
    def _extract_deposited_to(self, body: str, subject: str) -> str:
        """Extract where the money was deposited."""
        content = body + " " + subject
        
        # Log the content we're searching in
        self.logger.info(f"Searching for deposited_to in content: {content[:500]}...")
        
        # Look specifically for "Cash balance" in the email content first
        cash_balance_match = re.search(r'Cash\s+balance', content, re.IGNORECASE)
        if cash_balance_match:
            self.logger.info("Found 'Cash balance' in email content")
            return "Cash balance"
        
        # Look for Cash App specific deposit patterns as fallback
        deposit_patterns = [
            r"Deposited\s+to[:\s]+([A-Za-z']+(?:\s+[A-Za-z']+)*)",  # "Deposited to: Cash balance"
            r"Deposited\s+([A-Za-z']+(?:\s+[A-Za-z']+)*)",  # "Deposited Cash balance"
            r"([A-Za-z']+(?:\s+[A-Za-z']+)*)\s+balance",  # "Cash balance"
        ]
        
        for pattern in deposit_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                deposit = match.group(1).strip()
                self.logger.info(f"Cleaned deposit: '{deposit}'")
                # Clean up the deposit text using the helper method
                if deposit and len(deposit) > 2:
                    deposit = self._clean_name(deposit)
                    if deposit.lower() not in ["blockchain", "realty", "sender"]:
                        return deposit
        
        # Default for Cash App
        return "Cash balance"
    
    def _extract_transaction_number(self, body: str, subject: str) -> str:
        """Extract the actual Cash App transaction number with more permissive patterns.
        Prefer the exact value under a 'Transaction number' label (same line or next line).
        Fall back to #D- or /payments/ ids only when no explicit label is present.
        Explicitly reject 36-character UUIDs commonly present inside receipt URLs.
        """
        content = body + " " + subject
        raw = body + "\n" + subject  # preserve line breaks for next-line label detection

        # 1) Prefer explicit labeled transaction number capturing the entire label value (rest of the line)
        labelled_match = re.search(
            r"(?:Transaction|Payment|Confirmation)\s+(?:number|no\.?|id)[:\s-]*([^\n\r]+)",
            raw, re.IGNORECASE
        )
        
        # Also try the specific format we see in the logs: | #D-V8V9ODVK |
        if not labelled_match:
            pipe_match = re.search(r"\|.*?(#D[-A-Za-z0-9]+).*?\|", raw)
            if pipe_match:
                txn = pipe_match.group(1)
                self.logger.info(f"Found transaction number in pipe format: '{txn}'")
                return txn
        if labelled_match:
            txn = labelled_match.group(1).strip()
            txn = re.sub(r'<[^>]+>', '', txn).strip()
            txn = txn.strip(' \t\r\n.:;"')
            
            # If we got just pipes or other junk, ignore it and continue searching
            if txn and txn not in ['|', '||', '|||', '|  |']:
                if txn.upper().startswith('D') and not txn.startswith('#'):
                    txn = '#' + txn
                self.logger.info(f"Found explicit labelled transaction number: '{txn}'")
                return txn
            else:
                self.logger.info(f"Labelled match returned junk: '{txn}', continuing search...")

        # 2) If label is on its own line, look on the following lines for any non-empty value (take the full line)
        try:
            lines = [l.rstrip() for l in raw.splitlines()]
            for i, line in enumerate(lines):
                if 'transaction' in line.lower() and 'number' in line.lower():
                    for j in range(i+1, min(i+10, len(lines))):  # Increased range to search more lines
                        candidate = lines[j].strip()
                        candidate = re.sub(r'<[^>]+>', '', candidate).strip()
                        candidate = candidate.strip(' \t\r\n.:;"')
                        
                        # Skip empty lines and lines that are just pipes
                        if not candidate or candidate in ['|', '||', '|||', '|  |'] or re.match(r'^\|[\s|]*\|?$', candidate):
                            continue
                        
                        # Prefer lines that look like transaction numbers
                        if re.match(r'^[#]?[Dd]-[A-Za-z0-9-]+$', candidate):
                            if candidate and candidate.upper().startswith('D') and not candidate.startswith('#'):
                                candidate = '#' + candidate
                            self.logger.info(f"Found transaction number on following line (preferred): '{candidate}'")
                            return candidate
                        
                        # Also try to extract transaction number from the line using regex
                        txn_in_line = re.search(r'(#D[-A-Za-z0-9]+)', candidate)
                        if txn_in_line:
                            self.logger.info(f"Found transaction number in line (regex): '{txn_in_line.group(1)}'")
                            return txn_in_line.group(1)
                        
                        # Fallback: take first non-empty, non-pipe line
                        if len(candidate) > 1 and not candidate.startswith('|'):
                            self.logger.info(f"Found transaction number on following line (fallback): '{candidate}'")
                            return candidate
        except Exception:
            pass

        # 3) Common explicit patterns (keep broader matches as fallback)
        exact_patterns = [
            r"#D[-A-Za-z0-9]+",  # Explicit #D- pattern
            r"/payments/([A-Za-z0-9\-]{6,})",  # IDs in /payments/<id>/receipt URLs (but reject UUIDs)
            r"#([A-Za-z0-9-]+)",  # Simple "#123" format
            r"\|.*?(#D[-A-Za-z0-9]+).*?\|",  # Pattern for | #D-V8V9ODVK | format
        ]

        for pattern in exact_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                txn = match.group(1).strip() if match.groups() else match.group(0).strip()
                # If this looks like a 36-char UUID (common in receipt URLs), reject it
                if re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', txn, re.IGNORECASE):
                    self.logger.info(f"Found UUID-like id in content but rejecting as transaction number: '{txn}'")
                    continue
                if txn and not txn.startswith('#') and (txn.upper().startswith('D') or re.match(r'^D-[A-Za-z0-9-]+', txn, re.IGNORECASE)):
                    txn = '#' + txn
                self.logger.info(f"Found transaction number with fallback pattern '{pattern}': '{txn}'")
                return txn

        # 4) Try to find 'Transaction number' label with more permissive matching on single-line content
        label_match = re.search(r"Transaction\s+number[:\s#]*([#A-Za-z0-9-]+)", content, re.IGNORECASE)
        if label_match:
            transaction_number = label_match.group(1).strip()
            if re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', transaction_number, re.IGNORECASE):
                self.logger.info(f"Found UUID-like transaction_number under 'Transaction number' label but rejecting: '{transaction_number}'")
                return None
            if not transaction_number.startswith('#') and transaction_number.upper().startswith('D'):
                transaction_number = '#' + transaction_number
            self.logger.info(f"Found transaction number with label: '{transaction_number}'")
            return transaction_number

        # 5) Also try to extract IDs embedded in URLs (some emails have 'transaction/ID' style) but skip UUIDs
        url_id_match = re.search(r"/transaction[s]?/([A-Za-z0-9-]{6,})", content, re.IGNORECASE)
        if url_id_match:
            txn = url_id_match.group(1).strip()
            if re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', txn, re.IGNORECASE):
                self.logger.info(f"Found URL-embedded UUID but rejecting as transaction number: '{txn}'")
            else:
                self.logger.info(f"Found transaction id in url: '{txn}'")
                return txn

        # Fallback to None if no explicit transaction number found
        return None
    
    def _extract_transaction_date(self, body: str, subject: str) -> Optional[datetime]:
        """Extract the actual transaction date from email content."""
        content = body + " " + subject
        
        # Look for Cash App date patterns in the forwarded email header
        # Priority: Look for the actual Cash App email date, not the forwarded email date
        date_patterns = [
            r"From: Cash App <cash@square\.com>\r?\nDate: ([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s+at\s+(\d{1,2}:\d{2}:\d{2}\s+[AP]M\s+[A-Z]{3})",  # "Date: August 23, 2025 at 3:31:18 PM EDT"
            r"Date[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s+at\s+(\d{1,2}:\d{2}:\d{2}\s+[AP]M\s+[A-Z]{3})",  # "Date: August 23, 2025 at 3:31:18 PM EDT"
            r"([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s+at\s+(\d{1,2}:\d{2}:\d{2}\s+[AP]M\s+[A-Z]{3})",  # "August 23, 2025 at 3:31:18 PM EDT"
            r"(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\s+[AP]M)",  # "8/23/2025 3:31:18 PM EDT"
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    date_str = f"{match.group(1)} {match.group(2)}"
                    self.logger.info(f"Found date string: {date_str}")
                    # Parse the date string - you might need dateutil for better parsing
                    from dateutil import parser
                    parsed_date = parser.parse(date_str)
                    self.logger.info(f"Parsed date: {parsed_date}")
                    return parsed_date
                except Exception as e:
                    self.logger.warning(f"Failed to parse transaction date: {e}")
                    continue
        
        # Fallback to email date
        return None
    
    def _determine_transaction_type(self, body: str, subject: str) -> str:
        """Determine the type of transaction."""
        content = (body + " " + subject).lower()
        
        for pattern, txn_type in self.transaction_type_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return txn_type
        
        # Default to transfer if we can't determine
        return "transfer"

    def _extract_payment_status(self, body: str, subject: str) -> str:
        """Extract payment status from email content."""
        content = body + " " + subject
        
        # Look for common payment status patterns
        status_patterns = [
            r"Payment\s+has\s+completed",
            r"Payment\s+completed",
            r"(?:Status|Payment):\s*Completed",
            r"\bCompleted\b"
        ]
        
        for pattern in status_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "completed"
        
        # Default to completed since we only get emails for completed payments
        return "completed"
    
    def _extract_description(self, body: str, subject: str) -> Optional[str]:
        """Extract transaction description if available."""
        # Look for common description patterns
        description_patterns = [
            r"note[:\s]+([^\n\r]+)",
            r"memo[:\s]+([^\n\r]+)",
            r"description[:\s]+([^\n\r]+)",
        ]
        
        content = body + " " + subject
        
        for pattern in description_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                description = match.group(1).strip()
                if description and len(description) > 3:
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
        
        # Fallback to current time
        return datetime.now()
    
    def _generate_transaction_id(self, sender: str, recipient: str, amount: float, date: Optional[datetime]) -> str:
        """Generate a unique transaction ID."""
        import hashlib
        
        # Create a unique string from transaction details
        unique_string = f"{sender}_{recipient}_{amount}_{date}"
        
        # Generate hash
        hash_object = hashlib.md5(unique_string.encode())
        return hash_object.hexdigest()

    def _is_valid_name(self, name: Optional[str]) -> bool:
        """Return True when name looks like a real person/organization name (not a single letter or an email)."""
        if not name:
            return False
        name = name.strip()
        # reject obvious emails
        if '@' in name:
            return False
        # require at least two alphabetic characters in a row somewhere (prevents 'B' or 'R.').
        if not re.search(r"[A-Za-z]{2,}", name):
            return False
        # reject very short names
        if len(name) < 2:
            return False
        return True

    def _parse_display_name_from_header(self, header_value: str) -> Optional[str]:
        """Return a cleaned display name from an email header value using email.utils.parseaddr.
        Falls back to the local-part if no display name present (but only if it looks reasonable)."""
        from email.utils import parseaddr
        if not header_value:
            return None
        display, addr = parseaddr(header_value)
        display = (display or '').strip()
        addr = (addr or '').strip()
        # prefer display name if it looks valid
        if self._is_valid_name(display):
            return self._clean_name(display)
        # fallback: try local-part of addr (before @)
        if addr and '@' in addr:
            local = addr.split('@')[0]
            # turn dots/underscores into spaces and clean
            local_candidate = re.sub(r'[._]+', ' ', local).strip()
            if self._is_valid_name(local_candidate):
                return self._clean_name(local_candidate)
        return None
