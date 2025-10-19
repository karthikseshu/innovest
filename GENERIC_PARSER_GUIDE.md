# Generic Payment Parser Guide

## Overview

The **Generic Payment Parser** is a fallback parser that can extract transaction information from **any payment email**, not just Cash App. It automatically kicks in when no specific parser is found for an email sender.

## How It Works

### Parser Priority

1. **Specific Parsers First** (e.g., CashAppParser)
   - If email is from `cash@square.com` → CashAppParser handles it
   
2. **Generic Parser as Fallback** (GenericPaymentParser)
   - If no specific parser matches → Generic parser tries to extract data
   - Works with Venmo, Zelle, PayPal, Square, and ANY payment service

### Detection Logic

The generic parser identifies payment emails by looking for **2 or more** payment-related keywords:
- `payment`, `paid`, `sent you`, `you sent`, `received`
- `transaction`, `money`, `transfer`, `deposit`
- `$`, `usd`, `amount`, `total`

## Supported Patterns

### Amount Extraction
```
$123.45
$1,234.56
123.45 USD
Amount: $123.45
Total: $500.00
```

### Sender Extraction
```
John Doe sent you
sent by John Doe
from John Doe
Sender: John Doe
Paid by: John Doe
```

### Recipient Extraction
```
You sent $X to Jane Doe
sent to Jane Doe
to Jane Doe
Recipient: Jane Doe
Paid to: Jane Doe
```

### Transaction Number Extraction
```
#D-QQENK44E
#ABC123
Transaction number: #123456
Transaction ID: TXN-789
Reference: REF123
Confirmation: CONF456
```

## Usage Examples

### Example 1: Venmo Email

**API Call:**
```bash
curl -X POST "http://localhost:8000/api/v1/sync/sender/venmo@venmo.com?limit=10"
```

**Email Content:**
```
John Doe sent you $50.00
For: Dinner last night
Transaction ID: VEN-123456
```

**Extracted Data:**
```json
{
  "amount_paid": 50.0,
  "paid_by": "John Doe",
  "paid_to": "You",
  "transaction_number": "#VEN-123456",
  "source_provider": "venmo"
}
```

### Example 2: Zelle Email

**API Call:**
```bash
curl -X POST "http://localhost:8000/api/v1/sync/sender/noreply@zellepay.com?limit=10"
```

**Email Content:**
```
You sent $100 to Jane Smith
Transaction completed
Confirmation: ZEL-789012
```

**Extracted Data:**
```json
{
  "amount_paid": 100.0,
  "paid_by": "You",
  "paid_to": "Jane Smith",
  "transaction_number": "#ZEL-789012",
  "source_provider": "zellepay"
}
```

### Example 3: PayPal Email

**API Call:**
```bash
curl -X POST "http://localhost:8000/api/v1/sync/sender/service@paypal.com?limit=10"
```

**Email Content:**
```
Payment received from Bob Johnson
Amount: $250.00
Transaction ID: PP-456789
```

**Extracted Data:**
```json
{
  "amount_paid": 250.0,
  "paid_by": "Bob Johnson",
  "paid_to": "You",
  "transaction_number": "#PP-456789",
  "source_provider": "paypal"
}
```

### Example 4: Custom/Unknown Service

**API Call:**
```bash
curl -X POST "http://localhost:8000/api/v1/sync/sender/payments@customservice.com?limit=10"
```

**Email Content:**
```
You received a payment of $75
From: Alice Cooper
Reference: CUST-123
```

**Extracted Data:**
```json
{
  "amount_paid": 75.0,
  "paid_by": "Alice Cooper",
  "paid_to": "You",
  "transaction_number": "#CUST-123",
  "source_provider": "customservice"
}
```

## Provider Auto-Detection

The parser automatically detects the payment provider from the email address:

| Email Sender | Detected Provider |
|--------------|-------------------|
| `venmo@venmo.com` | `venmo` |
| `noreply@zellepay.com` | `zellepay` |
| `service@paypal.com` | `paypal` |
| `payments@square.com` | `square` |
| `xyz@unknown.com` | `unknown` |

## Response Format

```json
{
  "processed_emails": 10,
  "new_transactions": 8,
  "transactions": [
    {
      "amount_paid": 50.0,
      "paid_by": "John Doe",
      "paid_to": "You",
      "payment_status": "completed",
      "deposited_to": "Unknown",
      "transaction_number": "#VEN-123456",
      "transaction_date": "2025-08-27T15:30:00",
      "currency": "USD",
      "transaction_type": "received",
      "source_provider": "venmo",
      "integration_id": "uuid",
      "integration_user_id": "uuid"
    }
  ]
}
```

## Parser Behavior

### When Cash App Email is Detected
```
Email from: cash@square.com
↓
CashAppParser.can_parse() → True ✅
↓
GenericPaymentParser.can_parse() → False (skips Cash App)
↓
CashAppParser handles the email
```

### When Other Payment Email is Detected
```
Email from: venmo@venmo.com
↓
CashAppParser.can_parse() → False
↓
GenericPaymentParser.can_parse() → True ✅ (finds payment keywords)
↓
GenericPaymentParser handles the email
```

### When Non-Payment Email is Detected
```
Email from: newsletter@company.com
↓
CashAppParser.can_parse() → False
↓
GenericPaymentParser.can_parse() → False (no payment keywords)
↓
Email skipped (not parsed)
```

## Transaction Type Detection

The parser determines transaction type based on email content:

| Email Pattern | Transaction Type |
|---------------|------------------|
| "you sent $X" | `sent` |
| "sent you $X" | `received` |
| "payment request" | `request` |
| "refund" | `refund` |
| Other | `transfer` |

## Limitations

### What Works Well ✅
- Common payment email formats (sender, recipient, amount, transaction ID)
- Multiple payment services (Venmo, Zelle, PayPal, etc.)
- Auto-detection of payment provider
- Fallback for unknown services

### What May Not Work ⚠️
- **Non-standard formats**: If email doesn't follow typical payment patterns
- **Complex HTML emails**: Works best with plain text or simple HTML
- **Missing information**: Returns "Unknown" if data can't be extracted
- **Multiple transactions in one email**: Extracts only the first/main transaction

## Debugging

### Enable Debug Logging
```bash
LOG_LEVEL=DEBUG python -m uvicorn src.email_parser.api.main:app --reload
```

### Watch for These Log Messages
```
✅ Generic parser detected payment email from venmo@venmo.com (keywords: 3)
✅ Generic parser parsing email: Payment received
✅ Extracted amount: 50.0
✅ Found sender with pattern: John Doe
✅ Found transaction number: #VEN-123456
✅ Generic parser: Transaction parsing successful
```

### If Parsing Fails
Look for:
```
⚠️ Could not extract amount from email
⚠️ No suitable parser found for email
```

## Custom Parser Priority

If you want to add a specific parser for a service (e.g., VenmoParser), it will take priority:

```python
# In parser_factory.py
def _register_default_parsers(self):
    self.register_parser("cashapp", CashAppParser())
    self.register_parser("venmo", VenmoParser())  # Specific parser
    self.register_parser("generic_payment", GenericPaymentParser())  # Fallback
```

**Result:**
- Venmo emails → VenmoParser (more accurate)
- Other payment emails → GenericPaymentParser (fallback)
- Cash App emails → CashAppParser (original)

## Testing

### Test with Different Services

```bash
# Test Venmo
curl -X POST "http://localhost:8000/api/v1/sync/sender/venmo@venmo.com?limit=5"

# Test Zelle
curl -X POST "http://localhost:8000/api/v1/sync/sender/noreply@zellepay.com?limit=5"

# Test PayPal
curl -X POST "http://localhost:8000/api/v1/sync/sender/service@paypal.com?limit=5"

# Test any custom service
curl -X POST "http://localhost:8000/api/v1/sync/sender/payments@anyservice.com?limit=5"
```

### Expected Results

- ✅ Finds emails from the specified sender
- ✅ Extracts amount, sender, recipient
- ✅ Detects payment provider automatically
- ✅ Returns structured transaction data

## Next Steps

1. **Test with your payment services** - Try different email senders
2. **Review extracted data** - Check if parsing is accurate
3. **Add specific parsers** - Create dedicated parsers for services you use frequently
4. **Monitor logs** - Watch for parsing successes and failures

---

**The generic parser now handles ANY payment email automatically!** 🎉

No need to create a parser for each service - it "just works" as a smart fallback.

