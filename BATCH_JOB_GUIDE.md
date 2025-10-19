# Batch Job Endpoints Guide

## Overview

The email-reader now has **two types of endpoints**:

1. **Read-Only Endpoints** (`/sync/...`) - Return JSON, don't modify Supabase
2. **Batch Job Endpoints** (`/batch/...`) - Automatically insert into `staging.pay_transactions`

## Complete Endpoint List

### Read-Only Endpoints (Return JSON Only)

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/sync/sender/{sender_email}?limit=10` | Get transactions as JSON |
| `POST /api/v1/sync/sender/{sender_email}/date-range?start_date=...&end_date=...` | Get transactions in date range as JSON |

### Batch Job Endpoints (Auto-Insert to Supabase)

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/batch/sync-and-store/sender/{sender_email}?limit=10` | Extract AND insert to Supabase |
| `POST /api/v1/batch/sync-and-store/sender/{sender_email}/date-range?start_date=...&end_date=...` | Extract AND insert with date range |
| `POST /api/v1/batch/sync-and-store/all-providers?limit=10` | Process ALL payment providers at once |

## Batch Job Endpoints Details

### 1. Sync and Store by Sender

**Endpoint:**
```bash
POST /api/v1/batch/sync-and-store/sender/{sender_email}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/batch/sync-and-store/sender/cash@square.com?limit=10"
```

**What It Does:**
1. ✅ Fetches all active OAuth integrations from `api.email_integrations`
2. ✅ For each Gmail account, searches for emails FROM `cash@square.com`
3. ✅ Parses transactions from emails
4. ✅ **Automatically inserts** into `staging.pay_transactions`
5. ✅ Returns summary of what was processed and inserted

**Response:**
```json
{
  "batch_job": "sync-and-store",
  "sender_email": "cash@square.com",
  "processed_emails": 30,
  "parsed_transactions": 25,
  "parsing_errors": 5,
  "inserted_to_supabase": 23,
  "duplicates_skipped": 2,
  "insert_errors": 0,
  "insert_error_details": [],
  "message": "Processed 25 transactions, inserted 23 into Supabase",
  "timestamp": "2025-10-18T15:30:00"
}
```

### 2. Sync and Store by Sender with Date Range

**Endpoint:**
```bash
POST /api/v1/batch/sync-and-store/sender/{sender_email}/date-range
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/batch/sync-and-store/sender/cash@square.com/date-range?start_date=2025-08-01&end_date=2025-08-31"
```

**What It Does:**
1. ✅ Same as above, but only processes emails in the specified date range
2. ✅ **Automatically inserts** into `staging.pay_transactions`

**Response:**
```json
{
  "batch_job": "sync-and-store-date-range",
  "sender_email": "cash@square.com",
  "start_date": "2025-08-01",
  "end_date": "2025-08-31",
  "processed_emails": 50,
  "parsed_transactions": 45,
  "inserted_to_supabase": 43,
  "duplicates_skipped": 2,
  "message": "Processed 45 transactions, inserted 43 into Supabase"
}
```

### 3. Sync All Payment Providers

**Endpoint:**
```bash
POST /api/v1/batch/sync-and-store/all-providers
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/batch/sync-and-store/all-providers?limit=10"
```

**What It Does:**
1. ✅ Processes emails from **ALL common payment providers**:
   - Cash App (`cash@square.com`)
   - Venmo (`venmo@venmo.com`)
   - Zelle (`noreply@zellepay.com`)
   - PayPal (`service@paypal.com`, `service@intl.paypal.com`)
2. ✅ **Automatically inserts ALL** into `staging.pay_transactions`
3. ✅ Returns aggregated summary

**Response:**
```json
{
  "batch_job": "sync-all-providers",
  "providers_processed": 5,
  "total_emails_processed": 150,
  "total_transactions_parsed": 130,
  "total_inserted_to_supabase": 125,
  "total_duplicates": 5,
  "total_errors": 0,
  "provider_results": [
    {
      "provider": "cash@square.com",
      "emails_processed": 30,
      "transactions_parsed": 25,
      "inserted_to_supabase": 23,
      "duplicates": 2,
      "errors": 0
    },
    {
      "provider": "venmo@venmo.com",
      "emails_processed": 20,
      "transactions_parsed": 18,
      "inserted_to_supabase": 17,
      "duplicates": 1,
      "errors": 0
    }
  ],
  "message": "Batch job complete: Processed 130 transactions, inserted 125 into Supabase",
  "timestamp": "2025-10-18T15:30:00"
}
```

## Daily Batch Job Setup

### For Specific Sender (e.g., Cash App)

**Cron Schedule:** Daily at 2 AM
```bash
0 2 * * * curl -X POST "http://your-api.com/api/v1/batch/sync-and-store/sender/cash@square.com?limit=100"
```

### For All Payment Providers

**Cron Schedule:** Daily at 3 AM
```bash
0 3 * * * curl -X POST "http://your-api.com/api/v1/batch/sync-and-store/all-providers?limit=50"
```

### For Yesterday's Transactions

**Cron Schedule:** Daily at 4 AM
```bash
#!/bin/bash
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)
curl -X POST "http://your-api.com/api/v1/batch/sync-and-store/sender/cash@square.com/date-range?start_date=$YESTERDAY&end_date=$TODAY"
```

## What Gets Inserted to Supabase

### staging.pay_transactions Table

```sql
INSERT INTO staging.pay_transactions (
  user_id,              -- From api.email_integrations.user_id
  amount_paid,          -- Extracted from email
  paid_by,              -- Extracted from email
  paid_to,              -- Extracted from email
  payment_status,       -- "completed"
  transaction_number,   -- Cash App #D-XXX or generated hash
  transaction_date,     -- Email date in ISO 8601
  payment_provider,     -- "cashapp", "venmo", "zelle", etc.
  source,               -- "email-reader-api"
  raw_data,             -- Full transaction JSON
  created_by,           -- user_id
  updated_by            -- user_id
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
  '{"amount_paid": 450.0, ...}'::jsonb,
  '550e8400-e29b-41d4-a716-446655440000',
  '550e8400-e29b-41d4-a716-446655440000'
);
```

## Complete Workflow

### Example: Daily Cash App Batch Job

```
1. Cron triggers at 2 AM:
   curl POST /api/v1/batch/sync-and-store/sender/cash@square.com?limit=100
        ↓
2. Email-Reader API:
   - Query Supabase: SELECT * FROM api.email_integrations 
     WHERE integration_type='oauth' AND is_active=true
        ↓
3. Found 3 Gmail accounts:
   - account1@gmail.com (user_id: uuid-1)
   - account2@gmail.com (user_id: uuid-2)
   - account3@gmail.com (user_id: uuid-3)
        ↓
4. For EACH account:
   a. Refresh OAuth token if expired
   b. Connect to Gmail IMAP
   c. Search: FROM "cash@square.com" LIMIT 100
   d. Parse emails → 10 transactions (user_id: uuid-1)
        ↓
5. Total collected: 30 transactions across 3 accounts
        ↓
6. Insert into staging.pay_transactions:
   - INSERT transaction 1 (user_id: uuid-1) ✓
   - INSERT transaction 2 (user_id: uuid-1) ✓
   - INSERT transaction 3 (user_id: uuid-2) ✓
   - INSERT transaction 4 (user_id: uuid-2) - Duplicate (skip)
   - ... (25 more transactions)
        ↓
7. Return summary:
   {
     "inserted_to_supabase": 28,
     "duplicates_skipped": 2,
     "message": "Processed 30 transactions, inserted 28 into Supabase"
   }
```

## Answer to Your Question

### When you run:
```bash
curl -X POST "http://localhost:8000/api/v1/batch/sync-and-store/sender/karthik_seshu@yahoo.com?limit=10"
```

### Here's what happens:

1. ✅ Takes **all OAuth integrations** from `api.email_integrations` table
   - WHERE `integration_type = 'oauth'` AND `is_active = true`

2. ✅ For **each Gmail account** in those integrations:
   - Connects to that Gmail account
   - Searches for emails **FROM** `karthik_seshu@yahoo.com`
   - Extracts payment info from those emails

3. ✅ **Automatically inserts** into `staging.pay_transactions` with:
   - `user_id` = the `user_id` from that email integration
   - All transaction fields extracted from the email

4. ✅ Returns a summary showing what was inserted

### Key Points:

- ✅ **OAuth integrations** = Gmail accounts (not Yahoo accounts)
- ✅ **Sender email** = who sent the email (can be anyone: Yahoo, Venmo, Zelle, etc.)
- ✅ **Auto-inserts** to Supabase `staging.pay_transactions`
- ✅ Each transaction tagged with correct `user_id` from its Gmail account owner

## Endpoint Comparison

| Feature | `/sync/sender/...` | `/batch/sync-and-store/sender/...` |
|---------|-------------------|-----------------------------------|
| Fetches from Supabase integrations | ✅ Yes | ✅ Yes |
| Searches all Gmail accounts | ✅ Yes | ✅ Yes |
| Parses transactions | ✅ Yes | ✅ Yes |
| Returns JSON response | ✅ Yes | ✅ Yes |
| **Inserts to Supabase** | ❌ No | ✅ **YES** |
| Use case | Testing, manual review | Scheduled batch jobs |

## Monitoring Batch Jobs

### Check Logs
```bash
# Run with debug logging
LOG_LEVEL=DEBUG uvicorn src.email_parser.api.main:app --reload
```

### Watch for:
```
✅ Fetching active OAuth integrations from Supabase...
✅ Found 3 active OAuth integrations
✅ Processing emails for integration X
✅ Attempting to insert 25 transactions into Supabase
✅ Successfully inserted transaction: #D-QQENK44E
✅ Duplicate transaction skipped: #D-ABC123
✅ Insert summary: {"inserted_count": 23, "duplicate_count": 2}
```

## Error Handling

The batch job continues processing even if some insertions fail:

```json
{
  "inserted_to_supabase": 23,
  "insert_errors": 2,
  "insert_error_details": [
    {
      "transaction_number": "#D-XYZ",
      "error": "Missing user_id"
    },
    {
      "transaction_number": "#D-ABC",
      "error": "Invalid amount_paid"
    }
  ]
}
```

## Production Deployment

### Environment Variables Required

```bash
# In .env or production secrets
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### Cron Job Examples

**Option 1: Daily sync for specific sender**
```cron
# Daily at 2 AM - Cash App only
0 2 * * * curl -X POST "http://localhost:8000/api/v1/batch/sync-and-store/sender/cash@square.com?limit=100" >> /var/log/batch-job.log 2>&1
```

**Option 2: Daily sync for all providers**
```cron
# Daily at 3 AM - All payment providers
0 3 * * * curl -X POST "http://localhost:8000/api/v1/batch/sync-and-store/all-providers?limit=50" >> /var/log/batch-job.log 2>&1
```

**Option 3: Hourly sync with limit**
```cron
# Every hour - Cash App (latest 10 emails)
0 * * * * curl -X POST "http://localhost:8000/api/v1/batch/sync-and-store/sender/cash@square.com?limit=10" >> /var/log/batch-job.log 2>&1
```

## Summary

### Your Use Case:
```bash
curl -X POST "http://localhost:8000/api/v1/batch/sync-and-store/sender/karthik_seshu@yahoo.com?limit=10"
```

### What Happens:
1. ✅ Reads **all active OAuth integrations** from `api.email_integrations`
2. ✅ For each **Gmail account**:
   - Connects using OAuth token
   - Searches for emails FROM `karthik_seshu@yahoo.com`
   - Parses payment information
3. ✅ **Automatically inserts** to `staging.pay_transactions` with:
   - `user_id` = from the email integration owner
   - All transaction data extracted from email
4. ✅ Handles duplicates gracefully (skips them)
5. ✅ Returns summary of inserted/duplicate/error counts

**Perfect for scheduled daily batch jobs!** 🎉

