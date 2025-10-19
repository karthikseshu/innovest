# Updated API Response Format

## Overview

The API response now includes **all fields required** for the `staging.pay_transactions` table, including `user_id` from the email integration.

## Complete API Response

```json
{
  "processed_emails": 10,
  "new_transactions": 10,
  "errors": 0,
  "transactions": [
    {
      "amount_paid": 450.0,
      "paid_by": "Barbara Amador",
      "paid_to": "Blockchain Realty",
      "payment_status": "completed",
      "transaction_number": "#D-QQENK44E",
      "transaction_date": "2025-08-23T19:31:16+00:00",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "integration_id": "660e8400-e29b-41d4-a716-446655440000",
      "currency": "USD",
      "transaction_type": "Transfer",
      "deposited_to": "Cash balance",
      "source_provider": "cashapp"
    },
    {
      "amount_paid": 1000.0,
      "paid_by": "Blockchain Realty",
      "paid_to": "johanna R. almodovar",
      "payment_status": "completed",
      "transaction_number": "#D-VZ27REX2",
      "transaction_date": "2025-08-25T01:22:16+00:00",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "integration_id": "660e8400-e29b-41d4-a716-446655440000",
      "currency": "USD",
      "transaction_type": "Sent",
      "deposited_to": "Cash balance",
      "source_provider": "cashapp"
    }
  ],
  "duplicate_transactions": [],
  "message": "Successfully processed 10 new transactions",
  "Erros": []
}
```

## Field Descriptions

### Required Fields for `staging.pay_transactions`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `amount_paid` | Number | Transaction amount | `450.0` |
| `paid_by` | String | Sender name | `"Barbara Amador"` |
| `paid_to` | String | Recipient name | `"Blockchain Realty"` |
| `payment_status` | String | Status of payment | `"completed"` |
| `transaction_number` | String | Transaction ID | `"#D-QQENK44E"` |
| `transaction_date` | String (ISO 8601) | Transaction timestamp | `"2025-08-23T19:31:16+00:00"` |
| `user_id` | UUID String | User from email integration | `"550e8400-e29b-41d4-a716-..."` |

### Additional Metadata

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `integration_id` | UUID String | Email integration ID | `"660e8400-e29b-41d4-a716-..."` |
| `currency` | String | Currency code | `"USD"` |
| `transaction_type` | String | Type of transaction | `"Transfer"`, `"Sent"`, `"Received"` |
| `deposited_to` | String | Where money was deposited | `"Cash balance"` |
| `source_provider` | String | Payment service | `"cashapp"`, `"venmo"`, `"zelle"` |

## Field Sources

### `user_id` - From Email Integration

The `user_id` comes from the `api.email_integrations` table:

```
Email Integration (Supabase)
│
├─ user_id: 550e8400-e29b-41d4-a716-446655440000
├─ integration_type: "oauth"
├─ oauth_access_token: "ya29.xxxxx"
└─ is_active: true

↓ (Used to fetch Gmail emails)

Transaction Response
│
└─ user_id: 550e8400-e29b-41d4-a716-446655440000 ✓
```

### `transaction_number` - Intelligent Selection

```javascript
// Priority order:
transaction_number = 
  transaction.cashapp_transaction_number  // #D-QQENK44E (if found)
  || transaction.transaction_id;          // generated-hash (fallback)
```

### `transaction_date` - Email Date

The transaction date is extracted from:
1. **Email content** (if date found in body)
2. **Email header date** (fallback)

Always returned in ISO 8601 format with timezone.

## API Endpoints

### 1. Sync by Sender with Limit

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com?limit=10"
```

**Response:** See complete response above

### 2. Sync by Date Range

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com/date-range?start_date=2025-08-01&end_date=2025-08-31"
```

**Response:** Same format as above

## Multi-User Support

When processing emails from multiple Gmail accounts:

```json
{
  "transactions": [
    {
      "amount_paid": 450.0,
      "paid_by": "Barbara Amador",
      "user_id": "user-1-uuid",        // From Gmail Account 1
      "integration_id": "integration-1-uuid"
    },
    {
      "amount_paid": 300.0,
      "paid_by": "John Doe",
      "user_id": "user-2-uuid",        // From Gmail Account 2
      "integration_id": "integration-2-uuid"
    },
    {
      "amount_paid": 500.0,
      "paid_by": "Jane Smith",
      "user_id": "user-1-uuid",        // From Gmail Account 1 again
      "integration_id": "integration-1-uuid"
    }
  ]
}
```

Each transaction is tagged with the correct `user_id` from its source email integration.

## Inserting into Supabase

### JavaScript Example

```javascript
// Fetch transactions from email-reader API
const response = await fetch(
  'http://your-api.com/api/v1/sync/sender/cash@square.com?limit=10',
  { method: 'POST' }
);
const data = await response.json();

// Insert into staging.pay_transactions
const { data: inserted, error } = await supabase
  .from('pay_transactions')
  .insert(
    data.transactions.map(tx => ({
      user_id: tx.user_id,                    // ✓ From email integration
      amount_paid: tx.amount_paid,            // ✓ Required
      paid_by: tx.paid_by,                    // ✓ Required
      paid_to: tx.paid_to,                    // ✓ Required
      payment_status: tx.payment_status,      // ✓ Required
      transaction_number: tx.transaction_number, // ✓ Required
      transaction_date: tx.transaction_date,  // ✓ Required
      payment_provider: tx.source_provider,   // Optional
      raw_data: tx                            // Store full response
    }))
  );
```

### Python Example

```python
import requests
from supabase import create_client

# Fetch from email-reader API
response = requests.post(
    'http://your-api.com/api/v1/sync/sender/cash@square.com?limit=10'
)
data = response.json()

# Insert into Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

for tx in data['transactions']:
    result = supabase.table('pay_transactions').insert({
        'user_id': tx['user_id'],
        'amount_paid': tx['amount_paid'],
        'paid_by': tx['paid_by'],
        'paid_to': tx['paid_to'],
        'payment_status': tx['payment_status'],
        'transaction_number': tx['transaction_number'],
        'transaction_date': tx['transaction_date'],
        'payment_provider': tx['source_provider'],
        'raw_data': tx
    }).execute()
```

## Validation Checklist

Before inserting into Supabase, ensure:

- [x] `user_id` is a valid UUID
- [x] `amount_paid` is a positive number
- [x] `paid_by` is not empty
- [x] `paid_to` is not empty
- [x] `transaction_number` is not empty
- [x] `transaction_date` is valid ISO 8601 format
- [x] `payment_status` is one of: "completed", "pending", "failed", "cancelled"

## Changes from Previous Version

### ✅ Added

- `user_id` - **NEW**: UUID from `api.email_integrations.user_id`
- `integration_id` - **NEW**: Tracks which integration sourced this transaction
- `source_provider` - **NEW**: Payment service identifier

### ✅ Updated

- `transaction_date` - **NOW INCLUDED**: Previously missing in some responses
- `transaction_number` - **IMPROVED**: Now prioritizes actual Cash App #D-XXX numbers

### ❌ Removed

- Filter for "Blockchain Realty" only - **NOW RETURNS ALL TRANSACTIONS**

## Testing

```bash
# Test endpoint
curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com?limit=3"

# Expected fields in response
{
  "transactions": [
    {
      "amount_paid": ✓,
      "paid_by": ✓,
      "paid_to": ✓,
      "payment_status": ✓,
      "transaction_number": ✓,
      "transaction_date": ✓,  ← Must be present
      "user_id": ✓,           ← Must be present
      "integration_id": ✓,
      "currency": ✓,
      "transaction_type": ✓,
      "deposited_to": ✓,
      "source_provider": ✓
    }
  ]
}
```

---

## Summary

✅ **All fields for `staging.pay_transactions` are now included**
✅ **`user_id` correctly sourced from email integration**  
✅ **`transaction_date` always included in ISO 8601 format**
✅ **Ready for direct insertion into Supabase**
✅ **Multi-user support with proper user tracking**

The API response is now **100% compatible** with your Supabase table structure!

