# Sender Emails Configuration Guide

## Overview

The `sender_emails` field in `api.email_integrations` specifies **which email addresses to search for** when looking for payment transactions.

### Key Concept:
- **`email_username`**: The Gmail account to **login to** (e.g., `aiinnovest@gmail.com`)
- **`sender_emails`**: The email addresses to **search for** (e.g., `['cash@square.com', 'karthik_seshu@yahoo.com']`)

## How It Works

```
User's Gmail Account: aiinnovest@gmail.com
       ↓
Search for emails FROM: cash@square.com
Search for emails FROM: venmo@venmo.com
Search for emails FROM: karthik_seshu@yahoo.com
       ↓
Parse payment transactions
       ↓
Insert into staging.pay_transactions with user_id
```

## Setup

### Step 1: Add Column to Database

Run this SQL in Supabase SQL Editor:

```sql
ALTER TABLE api.email_integrations 
ADD COLUMN IF NOT EXISTS sender_emails TEXT[] DEFAULT ARRAY['cash@square.com'];
```

Or run the full migration file: `add_sender_emails_column.sql`

### Step 2: Configure Sender Emails

Update your integration records with the payment provider emails you want to search for:

```sql
-- For Cash App only
UPDATE api.email_integrations 
SET sender_emails = ARRAY['cash@square.com']
WHERE user_id = 'bcc9c52e-ae3f-4f5b-aa7e-359cbe3e3d81';

-- For multiple payment providers
UPDATE api.email_integrations 
SET sender_emails = ARRAY[
    'cash@square.com',
    'venmo@venmo.com',
    'service@paypal.com'
]
WHERE user_id = 'bcc9c52e-ae3f-4f5b-aa7e-359cbe3e3d81';

-- For personal email forwarding payment receipts
UPDATE api.email_integrations 
SET sender_emails = ARRAY['karthik_seshu@yahoo.com']
WHERE email_username = 'aiinnovest@gmail.com';
```

## Common Payment Provider Emails

| Provider | Sender Email |
|----------|-------------|
| **Cash App** | `cash@square.com` |
| **Venmo** | `venmo@venmo.com` |
| **PayPal** | `service@paypal.com` |
| **Zelle** | `noreply@zellepay.com` |
| **Apple Cash** | `no_reply@email.apple.com` |
| **Google Pay** | `googlepay-noreply@google.com` |
| **Personal** | Your custom email (e.g., `user@domain.com`) |

## Examples

### Example 1: Single Payment Provider

```sql
-- User only uses Cash App
UPDATE api.email_integrations 
SET sender_emails = ARRAY['cash@square.com']
WHERE email_username = 'user1@gmail.com';
```

**Result**: Searches `user1@gmail.com` for emails from `cash@square.com`

### Example 2: Multiple Payment Providers

```sql
-- User uses Cash App and Venmo
UPDATE api.email_integrations 
SET sender_emails = ARRAY['cash@square.com', 'venmo@venmo.com']
WHERE email_username = 'user2@gmail.com';
```

**Result**: 
- Searches `user2@gmail.com` for emails from `cash@square.com`
- Searches `user2@gmail.com` for emails from `venmo@venmo.com`

### Example 3: Personal Email Forwarding

```sql
-- User forwards payment receipts from their personal email
UPDATE api.email_integrations 
SET sender_emails = ARRAY['john.doe@yahoo.com']
WHERE email_username = 'business@gmail.com';
```

**Result**: Searches `business@gmail.com` for emails from `john.doe@yahoo.com`

### Example 4: Mixed Configuration

```sql
-- User receives Cash App directly and forwards from personal email
UPDATE api.email_integrations 
SET sender_emails = ARRAY[
    'cash@square.com',
    'personal@yahoo.com'
]
WHERE email_username = 'main@gmail.com';
```

## Default Behavior

If `sender_emails` is **not configured** (NULL or empty array):
- System defaults to: `['cash@square.com']`
- You'll see this in logs: `"Integration {id} has no sender_emails configured, using default: ['cash@square.com']"`

## Verification

### Check Current Configuration

```sql
SELECT 
    email_username,
    sender_emails,
    is_active
FROM api.email_integrations
WHERE integration_type = 'oauth';
```

### Test Manually

```bash
# Test with your Render API
curl -X POST "https://your-service.onrender.com/api/v1/batch/daily-sync?target_date=2025-10-18" \
  -H "X-API-Key: your_batch_job_api_key"
```

Check the response for `sender_emails` field in `integration_results`.

## Updating Configuration

You can update `sender_emails` at any time:

```sql
-- Add a new payment provider
UPDATE api.email_integrations 
SET sender_emails = array_append(sender_emails, 'venmo@venmo.com')
WHERE email_username = 'user@gmail.com';

-- Remove a payment provider
UPDATE api.email_integrations 
SET sender_emails = array_remove(sender_emails, 'venmo@venmo.com')
WHERE email_username = 'user@gmail.com';

-- Replace all sender emails
UPDATE api.email_integrations 
SET sender_emails = ARRAY['new@email.com']
WHERE email_username = 'user@gmail.com';
```

## Best Practices

### 1. Start Simple
Begin with one sender email and verify it works before adding more.

### 2. Use Official Payment Provider Emails
Always use the official email addresses from payment providers to ensure reliability.

### 3. Monitor Logs
Check the cron job logs to see which emails are being searched:
```
Processing integration d47b15d1... (aiinnovest@gmail.com): searching for emails from ['cash@square.com']
  → Searching for emails from cash@square.com
    ✓ cash@square.com: 3 emails, 3 transactions inserted
```

### 4. Avoid Too Many Senders
Each sender email triggers a separate Gmail API search. Keep it to 3-5 max per integration to avoid rate limits.

## Troubleshooting

### No transactions found?

1. **Verify sender email is correct**:
   ```sql
   SELECT sender_emails FROM api.email_integrations 
   WHERE email_username = 'your@gmail.com';
   ```

2. **Check if emails exist** in the Gmail account from that sender

3. **Check logs** for search details:
   ```
   → Searching for emails from cash@square.com
   - cash@square.com: No transactions found
   ```

### Wrong sender being searched?

Make sure you're setting `sender_emails` (plural) not `sender_email` (singular):
```sql
-- ✅ Correct
UPDATE api.email_integrations 
SET sender_emails = ARRAY['cash@square.com'];

-- ❌ Wrong
UPDATE api.email_integrations 
SET sender_email = 'cash@square.com';
```

## API Response Example

After configuration, the API response will include:

```json
{
  "integration_results": [
    {
      "integration_id": "d47b15d1-2f74-4336-b929-1a82c040f64c",
      "user_id": "bcc9c52e-ae3f-4f5b-aa7e-359cbe3e3d81",
      "email_username": "aiinnovest@gmail.com",
      "sender_emails": ["cash@square.com", "karthik_seshu@yahoo.com"],
      "emails_processed": 5,
      "transactions_parsed": 3,
      "inserted_to_supabase": 3,
      "duplicates": 0,
      "errors": 0
    }
  ]
}
```

## Summary

✅ **`email_username`**: Gmail account to login  
✅ **`sender_emails`**: Payment provider emails to search for  
✅ **Default**: `['cash@square.com']` if not configured  
✅ **Flexible**: Support multiple payment providers per user  
✅ **Dynamic**: Change configuration without code changes  

---

**Next Steps**: Run `add_sender_emails_column.sql` and configure your sender emails!

