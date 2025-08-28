import os, sys, json
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, "src")
from email_parser.core.email_client import EmailClient
from email_parser.parsers.cashapp_parser import CashAppParser

out = []
with EmailClient() as client:
    for msg in client.fetch_emails_by_sender("cash@square.com", limit=3):
        parser = CashAppParser()
        parsed = parser.parse_transaction(msg)
        raw = client.extract_email_body(msg)
        out.append({
            "subject": msg.get("subject"),
            "from": msg.get("from"),
            "to": msg.get("to"),
            "raw": raw,
            "parsed": parsed
        })
print(json.dumps(out, indent=2, default=str))