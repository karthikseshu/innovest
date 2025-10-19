# Supabase Multi-Account Integration

This document explains how the email-reader has been updated to support multiple Gmail accounts via Supabase OAuth integrations.

## Overview

The email-reader now connects to Supabase and processes emails from all active OAuth email integrations stored in the `api.email_integrations` table. This allows you to scan emails from multiple Gmail accounts without hardcoding credentials.

## Architecture

### Key Components

1. **Supabase Client** (`config/supabase.py`)
   - Connects to Supabase using service role key
   - Accesses the `api` schema where email integrations are stored

2. **OAuth Token Manager** (`src/email_parser/core/oauth_helper.py`)
   - Refreshes expired OAuth access tokens using refresh tokens
   - Updates tokens in Supabase after refresh

3. **Email Integration Manager** (`src/email_parser/core/email_integration_manager.py`)
   - Fetches active OAuth integrations from Supabase
   - Manages token refresh for each integration
   - Updates last_sync_at timestamps

4. **Multi-Account Email Client** (`src/email_parser/core/multi_account_email_client.py`)
   - Processes emails from all active integrations
   - Uses OAuth access tokens for IMAP authentication

5. **Multi-Account Transaction Processor** (`src/email_parser/core/multi_account_transaction_processor.py`)
   - Orchestrates email processing across multiple accounts
   - Parses transactions and returns consolidated results

## Setup

### 1. Install Dependencies

```bash
cd /Users/ranjani/Karthik/AI-Learning/email-reader
source venv/bin/activate
pip install -r requirements.txt
```

New dependencies added:
- `supabase` - Supabase Python client
- `postgrest-py` - PostgreSQL REST client
- `google-auth` - Google OAuth authentication
- `google-auth-oauthlib` - OAuth library
- `google-auth-httplib2` - HTTP transport for Google Auth

### 2. Configure Environment Variables

Create a `.env` file based on `env.example`:

```bash
# Supabase Configuration
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_from_supabase_dashboard

# Google OAuth Configuration (from Supabase Dashboard → Authentication → Providers → Google)
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
```

**Note:** The Supabase URL and anon key are hardcoded in `config/supabase.py` to match the innovest-ai project:
- URL: `https://dshlixmkpqpdnnixkykl.supabase.co`
- Anon Key: Already embedded in the code

### 3. Supabase Database Requirements

The email-reader expects the following table structure in Supabase:

**Table:** `api.email_integrations`

```sql
CREATE TABLE api.email_integrations (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  integration_type TEXT NOT NULL CHECK (integration_type IN ('oauth', 'manual')),
  
  -- OAuth fields
  oauth_provider TEXT,
  oauth_access_token TEXT,
  oauth_refresh_token TEXT,
  oauth_token_expiry TIMESTAMP WITH TIME ZONE,
  oauth_scopes TEXT[],
  
  -- Manual IMAP fields
  email_host TEXT,
  email_server TEXT,
  email_port INTEGER,
  email_username TEXT,
  email_key TEXT,
  email_use_ssl BOOLEAN DEFAULT true,
  
  -- Status
  is_active BOOLEAN DEFAULT true,
  last_sync_at TIMESTAMP WITH TIME ZONE,
  
  -- Audit fields
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by UUID,
  updated_by UUID
);
```

## Usage

### API Endpoints

The existing API endpoints now process emails from **all active OAuth integrations** in Supabase:

#### 1. Sync by Sender with Limit

```bash
curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com?limit=10"
```

**What it does:**
- Fetches all active OAuth integrations from Supabase
- For each integration:
  - Refreshes OAuth token if expired
  - Connects to Gmail IMAP using OAuth token
  - Searches for last 10 emails from `cash@square.com`
  - Parses transactions
- Returns consolidated results from all accounts

#### 2. Sync by Sender with Date Range

```bash
curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com/date-range?start_date=2025-08-01&end_date=2025-08-31"
```

**What it does:**
- Same as above, but filters emails by date range
- Processes all emails from the specified sender between start_date and end_date
- Consolidates results from all active OAuth accounts

### Response Format

```json
{
  "processed_emails": 30,
  "new_transactions": 25,
  "errors": 5,
  "transactions": [
    {
      "amount_paid": 450.0,
      "paid_by": "Barbara Amador",
      "paid_to": "Blockchain Realty",
      "payment_status": "completed",
      "deposited_to": "Cash balance",
      "transaction_number": "#D-QQENK44E",
      "transaction_date": "2025-08-23T19:31:16+00:00",
      "currency": "USD",
      "transaction_type": "Transfer",
      "integration_id": "uuid-of-integration",
      "integration_user_id": "uuid-of-user"
    }
  ],
  "duplicate_transactions": [],
  "message": "Successfully processed 25 new transactions",
  "Erros": []
}
```

## How OAuth Token Refresh Works

1. **Token Expiry Check**: Before processing emails, the system checks if the OAuth access token is expired (or expires within 5 minutes)

2. **Token Refresh**: If expired, it makes a request to Google's token endpoint:
   ```
   POST https://oauth2.googleapis.com/token
   {
     "client_id": "your_client_id",
     "client_secret": "your_client_secret",
     "refresh_token": "user_refresh_token",
     "grant_type": "refresh_token"
   }
   ```

3. **Update Supabase**: The new access token and expiry time are saved to `api.email_integrations`

4. **IMAP Connection**: The refreshed token is used as the password for Gmail IMAP authentication

## Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  API Request: GET /sync/sender/cash@square.com?limit=10    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│  MultiAccountTransactionProcessor                           │
│  - Initializes MultiAccountEmailClient                     │
└────────────────────┬───────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│  EmailIntegrationManager.get_active_oauth_integrations()   │
│  - Queries Supabase: api.email_integrations                │
│  - WHERE integration_type = 'oauth' AND is_active = true   │
│  - Returns List[EmailIntegration]                          │
└────────────────────┬───────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│  For Each Integration:                                      │
│                                                              │
│  1. OAuthTokenManager.refresh_access_token_if_needed()     │
│     - Check if token expired                                │
│     - Call Google OAuth token endpoint if needed           │
│     - Update Supabase with new token                       │
│                                                              │
│  2. EmailClient.__enter__()                                │
│     - Connect to imap.gmail.com:993                        │
│     - Login with email and OAuth access token              │
│                                                              │
│  3. EmailClient.search_emails_by_sender()                  │
│     - Search IMAP for emails from sender                   │
│     - Apply limit if specified                             │
│                                                              │
│  4. ParserFactory.find_parser_for_email()                  │
│     - Identify appropriate parser (CashAppParser, etc.)    │
│                                                              │
│  5. Parser.parse_transaction()                             │
│     - Extract transaction data from email                  │
│     - Return Transaction object                            │
│                                                              │
│  6. EmailIntegrationManager.update_last_sync()             │
│     - Update last_sync_at in Supabase                      │
└────────────────────┬───────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│  Return Consolidated Results                                │
│  - All transactions from all integrations                   │
│  - Processing statistics                                    │
│  - Errors (if any)                                         │
└────────────────────────────────────────────────────────────┘
```

## Backward Compatibility

The system still supports the old single-account mode using `.env` credentials:

- **Multi-Account Mode** (default): Uses Supabase OAuth integrations
- **Single-Account Mode** (fallback): Uses `EMAIL_USERNAME` and `EMAIL_PASSWORD` from `.env`

To use single-account mode, don't configure Supabase credentials and use the original `TransactionProcessor` instead of `MultiAccountTransactionProcessor`.

## Troubleshooting

### Issue: No integrations found

**Cause:** No active OAuth integrations in Supabase

**Solution:**
1. Check Supabase dashboard: `api.email_integrations` table
2. Ensure `integration_type = 'oauth'` and `is_active = true`
3. Verify `oauth_refresh_token` is not null

### Issue: Token refresh failed

**Cause:** Invalid Google OAuth credentials or revoked refresh token

**Solution:**
1. Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` match Supabase OAuth settings
2. Check if user revoked access to their Gmail account
3. User may need to re-authenticate via your OAuth flow

### Issue: IMAP connection failed

**Cause:** Invalid OAuth token or IMAP not enabled

**Solution:**
1. Ensure OAuth token is valid and not expired
2. Verify Gmail IMAP is enabled in user's account
3. Check if "Less secure app access" is configured (if needed)

## Testing

### Test with cURL

```bash
# Test endpoint health
curl http://localhost:8000/api/v1/health

# Test with limit
curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com?limit=5"

# Test with date range
curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com/date-range?start_date=2025-08-01&end_date=2025-08-31"
```

### Monitor Logs

```bash
# Run with debug logging
LOG_LEVEL=DEBUG python -m uvicorn src.email_parser.api.main:app --reload
```

Look for log messages like:
- `Fetching active OAuth integrations from Supabase...`
- `Found N active OAuth integrations`
- `OAuth token for integration X is expired, refreshing...`
- `Successfully refreshed and updated OAuth token`
- `Processing emails for integration X`

## Security Considerations

1. **Service Role Key**: Keep `SUPABASE_SERVICE_ROLE_KEY` secret - it has full database access
2. **OAuth Credentials**: Store `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` securely
3. **Access Tokens**: OAuth tokens are stored in Supabase - ensure RLS policies are configured
4. **Refresh Tokens**: Never expose refresh tokens - they provide long-term access

## Next Steps

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Configure `.env`**: Add Supabase and OAuth credentials
3. **Verify Supabase**: Ensure `api.email_integrations` has active OAuth records
4. **Test API**: Use cURL to test endpoints
5. **Monitor**: Check logs for OAuth refresh and email processing

## Support

For issues or questions, check:
- Supabase Dashboard for integration status
- Application logs for detailed error messages
- Google OAuth Console for credential verification

