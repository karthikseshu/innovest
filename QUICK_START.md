# Quick Start Guide - Multi-Account Email Reader

## Setup (5 minutes)

### 1. Install Dependencies
```bash
cd /Users/ranjani/Karthik/AI-Learning/email-reader
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Create `.env` file with:
```bash
# Copy from env.example
cp env.example .env

# Edit .env and add:
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
GOOGLE_CLIENT_ID=your_google_client_id  
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

**Where to find these:**
- **Service Role Key**: Supabase Dashboard → Settings → API → service_role key
- **Google OAuth**: Supabase Dashboard → Authentication → Providers → Google

### 3. Verify Supabase Data
Ensure you have active OAuth integrations in Supabase:
```sql
SELECT * FROM api.email_integrations 
WHERE integration_type = 'oauth' 
AND is_active = true;
```

### 4. Start Application
```bash
make run
# OR
uvicorn src.email_parser.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Test the Integration

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### Fetch Last 10 Transactions from All Accounts
```bash
curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com?limit=10"
```

### Fetch Transactions by Date Range
```bash
curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com/date-range?start_date=2025-08-01&end_date=2025-08-31"
```

## What to Expect

✅ **Success Response:**
```json
{
  "processed_emails": 30,
  "new_transactions": 25,
  "transactions": [
    {
      "amount_paid": 450.0,
      "paid_by": "Barbara Amador",
      "paid_to": "Blockchain Realty",
      "transaction_number": "#D-QQENK44E",
      "integration_id": "uuid",
      "integration_user_id": "uuid"
    }
  ],
  "message": "Successfully processed 25 new transactions"
}
```

## Logs to Monitor

Watch for these key messages:
```
✅ Fetching active OAuth integrations from Supabase...
✅ Found 3 active OAuth integrations
✅ OAuth token for integration X is still valid
✅ Successfully refreshed and updated OAuth token
✅ Processing emails for integration X (user: Y)
✅ Processed 10 emails from integration X
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No active OAuth integrations found" | Check Supabase `api.email_integrations` table |
| "Failed to refresh OAuth token" | Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` |
| "IMAP connection failed" | Ensure OAuth token is valid |
| "Permission denied" | Check `SUPABASE_SERVICE_ROLE_KEY` |

## Key Differences from Old Version

| Old (Single Account) | New (Multi-Account) |
|---------------------|---------------------|
| Uses `.env` credentials | Uses Supabase OAuth integrations |
| One email account | Multiple email accounts |
| Manual token management | Automatic OAuth refresh |
| No user tracking | Tracks which user/account |

## Production Deployment

For production, ensure:
1. Environment variables are set securely (not in .env file)
2. Supabase RLS policies protect email integrations
3. OAuth refresh tokens are encrypted at rest
4. Logs don't expose sensitive tokens
5. Rate limiting is configured for API endpoints

## Next Steps

1. ✅ Test with your Gmail accounts
2. ✅ Verify OAuth token refresh works
3. ✅ Monitor logs during processing
4. ✅ Integrate with your frontend/application
5. ✅ Set up error alerting for production

## Documentation

- **Full Integration Guide**: `SUPABASE_INTEGRATION.md`
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md`
- **This Quick Start**: `QUICK_START.md`

---

**Ready to test?** Run: `curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com?limit=5"`

