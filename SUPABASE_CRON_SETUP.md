# Supabase Cron Job Setup for Email-Reader

This guide explains how to set up a Supabase Edge Function with pg_cron to automatically sync payment transactions daily.

## Overview

- **Cron Schedule**: Runs at 2:00 AM EST every day
- **Target Date**: Processes emails from the previous day
- **Source**: Fetches all active OAuth integrations from `api.email_integrations`
- **Destination**: Inserts parsed transactions into `staging.pay_transactions`
- **API Endpoint**: Calls your Vercel-hosted email-reader API

## Architecture

```
┌─────────────────────┐
│  Supabase pg_cron   │
│  (2:00 AM EST)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Edge Function      │
│  (daily-email-sync) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Vercel API         │
│  (email-reader)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Gmail API          │
│  (fetch emails)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Supabase Database  │
│  staging.pay_trans  │
└─────────────────────┘
```

## Prerequisites

1. ✅ Email-reader API deployed to Vercel
2. ✅ `BATCH_JOB_API_KEY` set in Vercel environment variables
3. ✅ `api.email_integrations` table exists with OAuth records
4. ✅ `staging.pay_transactions` table exists
5. ✅ All permissions and RLS policies configured

## Setup Steps

### Step 1: Enable pg_cron Extension

Run this SQL in your Supabase SQL Editor:

```sql
-- Enable pg_cron extension
CREATE EXTENSION IF NOT EXISTS pg_cron;
```

### Step 2: Create Supabase Edge Function

1. Install Supabase CLI if you haven't:
   ```bash
   npm install -g supabase
   ```

2. Login to Supabase:
   ```bash
   supabase login
   ```

3. Link your project:
   ```bash
   supabase link --project-ref YOUR_PROJECT_REF
   ```

4. Create the Edge Function (see `supabase/functions/daily-email-sync/index.ts` file)

5. Deploy the Edge Function:
   ```bash
   supabase functions deploy daily-email-sync --no-verify-jwt
   ```

6. Set the required secrets:
   ```bash
   supabase secrets set VERCEL_API_URL=https://your-app.vercel.app
   supabase secrets set BATCH_JOB_API_KEY=your_batch_job_api_key
   ```

### Step 3: Schedule the Cron Job

Run this SQL in your Supabase SQL Editor (see `setup_cron_job.sql` file):

```sql
-- Schedule daily email sync at 2:00 AM EST (7:00 AM UTC)
SELECT cron.schedule(
  'daily-email-sync',           -- job name
  '0 7 * * *',                  -- cron expression (7:00 AM UTC = 2:00 AM EST)
  $$
  SELECT
    net.http_post(
      url := 'YOUR_EDGE_FUNCTION_URL/daily-email-sync',
      headers := '{"Content-Type": "application/json"}'::jsonb,
      body := '{}'::jsonb
    ) AS request_id;
  $$
);
```

## Cron Expression Explained

- `0 7 * * *` = Every day at 7:00 AM UTC (2:00 AM EST)
- Format: `minute hour day month weekday`

### Other Examples:
- Every 6 hours: `0 */6 * * *`
- Every day at midnight EST: `0 5 * * *`
- Every Monday at 2 AM EST: `0 7 * * 1`

## Monitoring

### Check Cron Job Status

```sql
-- List all cron jobs
SELECT * FROM cron.job;

-- Check cron job run history
SELECT * FROM cron.job_run_details 
ORDER BY start_time DESC 
LIMIT 10;

-- Check if job is enabled
SELECT jobid, jobname, schedule, active 
FROM cron.job 
WHERE jobname = 'daily-email-sync';
```

### View Logs

1. **Supabase Dashboard** → **Edge Functions** → **daily-email-sync** → **Logs**
2. **Supabase Dashboard** → **Database** → **Cron Jobs** → View execution history

## Troubleshooting

### Cron Job Not Running

```sql
-- Check if pg_cron extension is enabled
SELECT * FROM pg_extension WHERE extname = 'pg_cron';

-- Check if cron job exists
SELECT * FROM cron.job WHERE jobname = 'daily-email-sync';

-- Manually trigger the cron job (for testing)
SELECT cron.schedule(
  'test-email-sync',
  '* * * * *',  -- Every minute
  $$
  SELECT
    net.http_post(
      url := 'YOUR_EDGE_FUNCTION_URL/daily-email-sync',
      headers := '{"Content-Type": "application/json"}'::jsonb,
      body := '{}'::jsonb
    ) AS request_id;
  $$
);

-- Delete test job after testing
SELECT cron.unschedule('test-email-sync');
```

### Edge Function Errors

Check Edge Function logs in Supabase Dashboard for detailed error messages.

### API Errors

Check your Vercel deployment logs for API-related issues.

## Managing the Cron Job

### Disable Cron Job

```sql
-- Disable the cron job
UPDATE cron.job 
SET active = false 
WHERE jobname = 'daily-email-sync';
```

### Enable Cron Job

```sql
-- Enable the cron job
UPDATE cron.job 
SET active = true 
WHERE jobname = 'daily-email-sync';
```

### Delete Cron Job

```sql
-- Delete the cron job
SELECT cron.unschedule('daily-email-sync');
```

### Update Cron Schedule

```sql
-- Delete old schedule
SELECT cron.unschedule('daily-email-sync');

-- Create new schedule
SELECT cron.schedule(
  'daily-email-sync',
  '0 8 * * *',  -- New time: 8:00 AM UTC = 3:00 AM EST
  $$
  SELECT
    net.http_post(
      url := 'YOUR_EDGE_FUNCTION_URL/daily-email-sync',
      headers := '{"Content-Type": "application/json"}'::jsonb,
      body := '{}'::jsonb
    ) AS request_id;
  $$
);
```

## Testing

### Test Manually (Local)

```bash
# Test with today's date
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync?target_date=2025-10-18" \
  -H "X-API-Key: your_batch_job_api_key"
```

### Test Edge Function (After Deployment)

```bash
curl -X POST "https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Security Notes

1. ✅ `BATCH_JOB_API_KEY` is stored as a secret in both Vercel and Supabase
2. ✅ Edge Function uses `--no-verify-jwt` since it's triggered by cron
3. ✅ API endpoint validates the API key before processing
4. ✅ Service role key is used for database operations

## Cost Considerations

- **Edge Functions**: First 500K requests/month free, then $2 per million
- **pg_cron**: No additional cost (included in Supabase)
- **Gmail API**: 1 billion quota units per day (free)
- **Vercel**: Functions included in all plans

Running once per day = ~30 requests/month (negligible cost)

## Next Steps

1. Deploy email-reader to Vercel
2. Set up Supabase Edge Function
3. Schedule the cron job
4. Monitor the first few runs
5. Verify data in `staging.pay_transactions`

## Support

If you encounter issues:
1. Check Supabase Edge Function logs
2. Check Vercel deployment logs
3. Check cron job execution history
4. Verify API key is correct
5. Test the API endpoint manually

