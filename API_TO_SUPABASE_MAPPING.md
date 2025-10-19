# API Response to Supabase Table Mapping

## Overview

This document shows how the email-reader API response maps to the `staging.pay_transactions` table in Supabase.

## API Response Format

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
      "user_id": "uuid-from-email-integration",
      "integration_id": "uuid-of-integration",
      "currency": "USD",
      "transaction_type": "Transfer",
      "deposited_to": "Cash balance",
      "source_provider": "cashapp"
    }
  ],
  "message": "Successfully processed 10 new transactions"
}
```

## Field Mapping to `staging.pay_transactions`

| API Response Field | Supabase Column | Type | Required | Notes |
|-------------------|-----------------|------|----------|-------|
| `amount_paid` | `amount_paid` | NUMERIC(12,2) | ✅ Yes | Transaction amount |
| `paid_by` | `paid_by` | TEXT | ✅ Yes | Sender name |
| `paid_to` | `paid_to` | TEXT | ✅ Yes | Recipient name |
| `payment_status` | `payment_status` | TEXT | ✅ Yes | Always "completed" |
| `transaction_number` | `transaction_number` | TEXT | ✅ Yes | Cash App #D-XXX or generated hash |
| `transaction_date` | `transaction_date` | TIMESTAMP WITH TIME ZONE | ✅ Yes | ISO 8601 format |
| `user_id` | `user_id` | UUID | ✅ Yes | From `api.email_integrations.user_id` |
| `source_provider` | `payment_provider` | TEXT | ❌ No | Optional: "cashapp", "venmo", etc. |

## Supabase Table Schema

```sql
CREATE TABLE staging.pay_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Transaction details from email-reader API
    amount_paid NUMERIC(12,2) NOT NULL,
    paid_by TEXT NOT NULL,
    paid_to TEXT NOT NULL,
    payment_status TEXT NOT NULL DEFAULT 'completed',
    transaction_number TEXT NOT NULL,
    transaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Metadata fields
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    payment_provider TEXT DEFAULT 'cashapp',
    source TEXT DEFAULT 'email-reader-api',
    raw_data JSONB,
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    created_by UUID REFERENCES auth.users(id),
    updated_by UUID REFERENCES auth.users(id),
    
    CONSTRAINT unique_transaction_per_user UNIQUE(user_id, transaction_number, payment_provider)
);
```

## Inserting Data into Supabase

### Method 1: Using Supabase Function

```javascript
// Frontend/Backend code to insert transactions
const { data, error } = await supabase
  .rpc('insert_pay_transactions', {
    p_user_id: transaction.user_id,
    p_transactions: response.transactions,
    p_payment_provider: 'cashapp'
  });
```

### Method 2: Direct Insert

```javascript
// Loop through transactions and insert
for (const transaction of response.transactions) {
  const { data, error } = await supabase
    .from('pay_transactions')
    .insert({
      user_id: transaction.user_id,
      amount_paid: transaction.amount_paid,
      paid_by: transaction.paid_by,
      paid_to: transaction.paid_to,
      payment_status: transaction.payment_status,
      transaction_number: transaction.transaction_number,
      transaction_date: transaction.transaction_date,
      payment_provider: transaction.source_provider,
      source: 'email-reader-api',
      raw_data: transaction,
      created_by: transaction.user_id,
      updated_by: transaction.user_id
    })
    .select();
}
```

### Method 3: Bulk Insert with upsert

```javascript
// Bulk insert/update transactions
const transactionsToInsert = response.transactions.map(tx => ({
  user_id: tx.user_id,
  amount_paid: tx.amount_paid,
  paid_by: tx.paid_by,
  paid_to: tx.paid_to,
  payment_status: tx.payment_status,
  transaction_number: tx.transaction_number,
  transaction_date: tx.transaction_date,
  payment_provider: tx.source_provider || 'cashapp',
  source: 'email-reader-api',
  raw_data: tx,
  created_by: tx.user_id,
  updated_by: tx.user_id
}));

const { data, error } = await supabase
  .from('pay_transactions')
  .upsert(transactionsToInsert, {
    onConflict: 'user_id,transaction_number,payment_provider'
  })
  .select();
```

## Example Integration Flow

```javascript
// 1. Call email-reader API
const response = await fetch(
  'http://your-email-reader-api.com/api/v1/sync/sender/cash@square.com?limit=10',
  { method: 'POST' }
);
const data = await response.json();

// 2. Insert into Supabase
const { data: inserted, error } = await supabase
  .from('pay_transactions')
  .insert(
    data.transactions.map(tx => ({
      user_id: tx.user_id,
      amount_paid: tx.amount_paid,
      paid_by: tx.paid_by,
      paid_to: tx.paid_to,
      payment_status: tx.payment_status,
      transaction_number: tx.transaction_number,
      transaction_date: tx.transaction_date,
      payment_provider: tx.source_provider,
      raw_data: tx
    }))
  );

// 3. Handle response
if (error) {
  console.error('Error inserting transactions:', error);
} else {
  console.log(`Inserted ${inserted.length} transactions`);
}
```

## Field Details

### `user_id` Source

The `user_id` comes from the `api.email_integrations` table:

```sql
-- How user_id is obtained
SELECT user_id, oauth_access_token 
FROM api.email_integrations 
WHERE integration_type = 'oauth' 
AND is_active = true;
```

Each transaction is tagged with the `user_id` from the email integration that fetched it, ensuring:
- ✅ Transactions are associated with the correct user
- ✅ Multi-account support (different users can have their own transactions)
- ✅ RLS policies work correctly (users see only their transactions)

### `transaction_number` Format

| Provider | Format | Example |
|----------|--------|---------|
| Cash App | `#D-XXXXXX` | `#D-QQENK44E` |
| Venmo | `#VEN-XXXXXX` | `#VEN-123456` |
| Zelle | `#ZEL-XXXXXX` | `#ZEL-789012` |
| Generic/Unknown | MD5 Hash | `fb8c35e38da91453aac4cbb570b8df37` |

### `transaction_date` Format

Always in ISO 8601 format with timezone:
```
2025-08-23T19:31:16+00:00
```

PostgreSQL automatically converts this to `TIMESTAMP WITH TIME ZONE`.

### `payment_status`

Currently always returns `"completed"` since we only parse completed transactions from emails.

Possible future values:
- `completed` (current)
- `pending`
- `failed`
- `cancelled`

## Complete Example

### API Request
```bash
curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com?limit=5"
```

### API Response
```json
{
  "processed_emails": 5,
  "new_transactions": 5,
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
    }
  ]
}
```

### Supabase Insert
```sql
INSERT INTO staging.pay_transactions (
  user_id,
  amount_paid,
  paid_by,
  paid_to,
  payment_status,
  transaction_number,
  transaction_date,
  payment_provider,
  source,
  raw_data
) VALUES (
  '550e8400-e29b-41d4-a716-446655440000',
  450.00,
  'Barbara Amador',
  'Blockchain Realty',
  'completed',
  '#D-QQENK44E',
  '2025-08-23T19:31:16+00:00',
  'cashapp',
  'email-reader-api',
  '{"amount_paid": 450.0, "paid_by": "Barbara Amador", ...}'::jsonb
);
```

## Data Validation

Before inserting into Supabase, validate:

```javascript
function validateTransaction(tx) {
  const errors = [];
  
  // Required fields
  if (!tx.user_id) errors.push('user_id is required');
  if (!tx.amount_paid || tx.amount_paid <= 0) errors.push('amount_paid must be positive');
  if (!tx.paid_by) errors.push('paid_by is required');
  if (!tx.paid_to) errors.push('paid_to is required');
  if (!tx.transaction_number) errors.push('transaction_number is required');
  if (!tx.transaction_date) errors.push('transaction_date is required');
  
  // Validate UUID format
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (tx.user_id && !uuidRegex.test(tx.user_id)) {
    errors.push('user_id must be a valid UUID');
  }
  
  // Validate date format
  if (tx.transaction_date && isNaN(Date.parse(tx.transaction_date))) {
    errors.push('transaction_date must be a valid ISO 8601 date');
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}
```

## Error Handling

```javascript
async function insertTransactions(transactions) {
  const results = {
    inserted: 0,
    failed: 0,
    errors: []
  };
  
  for (const tx of transactions) {
    // Validate
    const validation = validateTransaction(tx);
    if (!validation.valid) {
      results.failed++;
      results.errors.push({
        transaction_number: tx.transaction_number,
        errors: validation.errors
      });
      continue;
    }
    
    // Insert
    const { data, error } = await supabase
      .from('pay_transactions')
      .insert({
        user_id: tx.user_id,
        amount_paid: tx.amount_paid,
        paid_by: tx.paid_by,
        paid_to: tx.paid_to,
        payment_status: tx.payment_status,
        transaction_number: tx.transaction_number,
        transaction_date: tx.transaction_date,
        payment_provider: tx.source_provider || 'cashapp',
        raw_data: tx
      })
      .select();
    
    if (error) {
      results.failed++;
      results.errors.push({
        transaction_number: tx.transaction_number,
        error: error.message
      });
    } else {
      results.inserted++;
    }
  }
  
  return results;
}
```

## Summary

✅ **All Required Fields Included:**
- `amount_paid` ✓
- `paid_by` ✓
- `paid_to` ✓
- `payment_status` ✓
- `transaction_number` ✓
- `transaction_date` ✓
- `user_id` ✓ (from `api.email_integrations`)

✅ **Additional Metadata:**
- `integration_id` - Links to specific email integration
- `source_provider` - Payment service (cashapp, venmo, etc.)
- `currency` - Always USD currently
- `transaction_type` - sent/received/transfer

The API response is now **fully compatible** with the `staging.pay_transactions` table structure!

