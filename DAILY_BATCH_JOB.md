# Daily Batch Job - Complete Guide

## Overview

The **Daily Batch Job** endpoint is designed to run on a schedule (e.g., daily at 2 AM) to automatically:
1. Fetch all OAuth integrations from Supabase
2. Process payment emails for each user
3. Insert transactions into `staging.pay_transactions`

## The Main Batch Endpoint

### Endpoint
```bash
POST /api/v1/batch/daily-sync
```

### What It Does

```
1. Fetch OAuth Integrations from Supabase
   ↓
   SELECT * FROM api.email_integrations 
   WHERE integration_type='oauth' AND is_active=true
   
   Returns:
   ├─ Integration 1: user_id=uuid-1, email_username=john@gmail.com
   ├─ Integration 2: user_id=uuid-2, email_username=jane@gmail.com
   └─ Integration 3: user_id=uuid-3, email_username=bob@gmail.com

2. For EACH Integration
   ↓
   Integration 1 (john@gmail.com):
   ├─ Refresh OAuth token if expired
   ├─ Connect to john@gmail.com's Gmail
   ├─ Search: FROM "john@gmail.com" (searches for payment emails FROM this user)
   ├─ Date range: 2025-10-18 00:00:00 to 2025-10-18 23:59:59
   ├─ Parse emails → 5 transactions
   └─ Tag each with user_id: uuid-1
   
   Integration 2 (jane@gmail.com):
   ├─ Refresh OAuth token if expired
   ├─ Connect to jane@gmail.com's Gmail
   ├─ Search: FROM "jane@gmail.com"
   ├─ Parse emails → 3 transactions
   └─ Tag each with user_id: uuid-2
   
   Integration 3 (bob@gmail.com):
   ├─ Same process → 7 transactions
   └─ Tag each with user_id: uuid-3

3. Insert ALL Transactions to Supabase
   ↓
   INSERT INTO staging.pay_transactions
   ├─ 5 transactions (user_id: uuid-1) ✓
   ├─ 3 transactions (user_id: uuid-2) ✓
   └─ 7 transactions (user_id: uuid-3) ✓
   
   Total: 15 transactions inserted

4. Return Summary
   {
     "integrations_processed": 3,
     "total_transactions_parsed": 15,
     "total_inserted_to_supabase": 15
   }
```

## Usage Examples

### Example 1: Process Today's Transactions

```bash
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync"
```

**What happens:**
- Processes emails from **today** (current date)
- Uses `email_username` from each integration as sender to search for
- Inserts to Supabase automatically

### Example 2: Process Yesterday's Transactions

```bash
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync?target_date=2025-10-17"
```

**What happens:**
- Processes emails from **October 17, 2025** (full day: 00:00:00 to 23:59:59)
- Same workflow as above

### Example 3: Process Specific Date

```bash
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync?target_date=2025-08-23"
```

## Response Format

```json
{
  "batch_job": "daily-sync",
  "target_date": "2025-10-18",
  "start_datetime": "2025-10-18T00:00:00",
  "end_datetime": "2025-10-18T23:59:59",
  "integrations_processed": 3,
  "total_emails_processed": 45,
  "total_transactions_parsed": 38,
  "total_inserted_to_supabase": 36,
  "total_duplicates": 2,
  "total_errors": 0,
  "integration_results": [
    {
      "integration_id": "integration-1-uuid",
      "user_id": "user-1-uuid",
      "email_username": "john@gmail.com",
      "emails_processed": 15,
      "transactions_parsed": 12,
      "inserted_to_supabase": 12,
      "duplicates": 0,
      "errors": 0
    },
    {
      "integration_id": "integration-2-uuid",
      "user_id": "user-2-uuid",
      "email_username": "jane@gmail.com",
      "emails_processed": 18,
      "transactions_parsed": 15,
      "inserted_to_supabase": 13,
      "duplicates": 2,
      "errors": 0
    },
    {
      "integration_id": "integration-3-uuid",
      "user_id": "user-3-uuid",
      "email_username": "bob@gmail.com",
      "emails_processed": 12,
      "transactions_parsed": 11,
      "inserted_to_supabase": 11,
      "duplicates": 0,
      "errors": 0
    }
  ],
  "message": "Daily batch complete: Processed 38 transactions, inserted 36 into Supabase",
  "timestamp": "2025-10-18T02:00:00"
}
```

## Scheduled Batch Job Setup

### Cron Job (Daily at 2 AM for Today)

```cron
# Process today's transactions daily at 2 AM
0 2 * * * curl -X POST "http://localhost:8000/api/v1/batch/daily-sync" >> /var/log/email-reader-batch.log 2>&1
```

### Cron Job (Daily at 2 AM for Yesterday)

```bash
#!/bin/bash
# batch-job.sh
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync?target_date=$YESTERDAY"
```

```cron
# Run daily at 2 AM for yesterday's data
0 2 * * * /path/to/batch-job.sh >> /var/log/email-reader-batch.log 2>&1
```

### Cron Job (Hourly for Today)

```cron
# Process today's transactions every hour
0 * * * * curl -X POST "http://localhost:8000/api/v1/batch/daily-sync" >> /var/log/email-reader-batch.log 2>&1
```

## How It Works - Detailed Example

### Scenario

You have 2 users who connected their Gmail accounts:

**api.email_integrations table:**
```sql
| id    | user_id | email_username        | integration_type | is_active |
|-------|---------|----------------------|------------------|-----------|
| int-1 | user-1  | john@gmail.com       | oauth            | true      |
| int-2 | user-2  | jane@yahoo.com       | oauth            | true      |
```

### When Batch Job Runs:

```bash
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync?target_date=2025-10-18"
```

**Step 1: Fetch Integrations**
```
Found 2 integrations:
- john@gmail.com (user: user-1)
- jane@yahoo.com (user: user-2)
```

**Step 2: Process Integration 1 (john@gmail.com)**
```
- Connect to john@gmail.com's Gmail account
- Search: FROM "john@gmail.com" 
  Date: 2025-10-18 00:00:00 to 2025-10-18 23:59:59
- Found emails:
  ├─ Cash App: "You sent $500 to Alice" → Parse ✓
  ├─ Venmo: "You paid $50 to Bob" → Parse ✓
  └─ Zelle: "You sent $100 to Charlie" → Parse ✓
- Total: 3 transactions (all tagged with user_id: user-1)
```

**Step 3: Process Integration 2 (jane@yahoo.com)**
```
- Connect to jane@yahoo.com's Gmail account (OAuth linked to Yahoo)
- Search: FROM "jane@yahoo.com"
  Date: 2025-10-18 00:00:00 to 2025-10-18 23:59:59
- Found emails:
  ├─ Cash App: "Jane sent $200 to David" → Parse ✓
  └─ PayPal: "Jane sent $75 to Eve" → Parse ✓
- Total: 2 transactions (all tagged with user_id: user-2)
```

**Step 4: Insert to Supabase**
```sql
-- Transaction 1 (John's)
INSERT INTO staging.pay_transactions (
  user_id, amount_paid, paid_by, paid_to, transaction_number, ...
) VALUES (
  'user-1', 500.00, 'john@gmail.com', 'Alice', '#D-ABC123', ...
); ✓

-- Transaction 2 (John's)
INSERT ... VALUES ('user-1', 50.00, 'john@gmail.com', 'Bob', ...); ✓

-- Transaction 3 (John's)
INSERT ... VALUES ('user-1', 100.00, 'john@gmail.com', 'Charlie', ...); ✓

-- Transaction 4 (Jane's)
INSERT ... VALUES ('user-2', 200.00, 'jane@yahoo.com', 'David', ...); ✓

-- Transaction 5 (Jane's)
INSERT ... VALUES ('user-2', 75.00, 'jane@yahoo.com', 'Eve', ...); ✓
```

**Step 5: Return Summary**
```json
{
  "integrations_processed": 2,
  "total_transactions_parsed": 5,
  "total_inserted_to_supabase": 5,
  "integration_results": [
    {
      "integration_id": "int-1",
      "user_id": "user-1",
      "email_username": "john@gmail.com",
      "transactions_parsed": 3,
      "inserted_to_supabase": 3
    },
    {
      "integration_id": "int-2",
      "user_id": "user-2",
      "email_username": "jane@yahoo.com",
      "transactions_parsed": 2,
      "inserted_to_supabase": 2
    }
  ]
}
```

## Important Notes

### What `email_username` Is Used For

The `email_username` field in `api.email_integrations` is used as the **sender email to search for**.

**Why?** Because when you send money via Cash App/Venmo/etc., the confirmation email is FROM your own email address (or the service sends you a copy).

**Example:**
- User's email: `john@gmail.com`
- User sends $500 via Cash App
- Cash App sends confirmation TO: `john@gmail.com` FROM: `cash@square.com`
- Batch job searches john's Gmail for emails FROM `john@gmail.com` OR `cash@square.com`

### Dynamic Sender Email

The batch job **dynamically uses** `email_username` from each integration:

```python
# For each integration:
sender_email = integration.email_username  # "john@gmail.com"

# Then searches:
search_emails_by_sender_date_range(
    sender_email=sender_email,  # Dynamically set!
    start_date=start_of_day,
    end_date=end_of_day
)
```

## All Batch Endpoints Summary

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `/batch/daily-sync` | **Process all integrations for a day** | **Main scheduled batch job** ⭐ |
| `/batch/sync-and-store/sender/{email}` | Process specific sender | Ad-hoc sync for one provider |
| `/batch/sync-and-store/sender/{email}/date-range` | Process specific sender + date range | Historical data sync |

## Recommended Setup

### Production Cron Job

```cron
# Daily at 2 AM - Process today's transactions for all users
0 2 * * * curl -X POST "http://your-api.com/api/v1/batch/daily-sync" >> /var/log/email-batch.log 2>&1

# OR process yesterday's transactions
0 2 * * * curl -X POST "http://your-api.com/api/v1/batch/daily-sync?target_date=$(date -d yesterday +\%Y-\%m-\%d)" >> /var/log/email-batch.log 2>&1
```

### Monitor Logs

```bash
tail -f /var/log/email-batch.log
```

Look for:
```
✅ Processing daily batch for 3 OAuth integrations on 2025-10-18
✅ Processing integration int-1: searching for emails from john@gmail.com
✅ Successfully inserted transaction: #D-ABC123
✅ Daily batch complete: Processed 38 transactions, inserted 36 into Supabase
```

## Error Handling

The batch job is resilient:
- ✅ Continues if one integration fails
- ✅ Skips duplicates automatically
- ✅ Reports errors per integration
- ✅ Updates `last_sync_at` only on success

## Testing

### Test Today's Batch
```bash
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync"
```

### Test Specific Date
```bash
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync?target_date=2025-08-23"
```

### Verify in Supabase
```sql
-- Check inserted transactions
SELECT 
  user_id, 
  paid_by, 
  paid_to, 
  amount_paid, 
  transaction_date,
  created_at
FROM staging.pay_transactions 
WHERE DATE(transaction_date) = '2025-10-18'
ORDER BY created_at DESC;

-- Check last sync per integration
SELECT 
  id,
  user_id,
  email_username,
  last_sync_at,
  is_active
FROM api.email_integrations
WHERE integration_type = 'oauth'
ORDER BY last_sync_at DESC;
```

---

## 🎯 Final Answer to Your Question

### Your Design:
> "Batch job calls the endpoint which should go to api.email_integrations table, take all oauth records, take the 'email_username' and dynamically use that to search for emails, and insert into staging.pay_transactions"

### ✅ Implemented Exactly As You Described!

**Batch Job Endpoint:**
```bash
POST /api/v1/batch/daily-sync?target_date=2025-10-18
```

**What It Does:**
1. ✅ Goes to `api.email_integrations` table
2. ✅ Takes all OAuth records where `is_active=true`
3. ✅ For each record:
   - Takes `email_username` (e.g., `john@gmail.com`)
   - Dynamically uses it as the sender to search for
   - Searches that Gmail inbox for payment emails from that sender
   - Processes emails for the full target date (00:00 to 23:59)
4. ✅ Automatically inserts to `staging.pay_transactions` with correct `user_id`

**Perfect for your daily scheduled batch job!** 🎉

