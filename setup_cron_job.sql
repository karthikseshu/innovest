-- ============================================
-- Supabase Cron Job Setup for Daily Email Sync
-- ============================================
-- This script sets up a daily cron job to sync payment transactions from emails
-- Run this in your Supabase SQL Editor after deploying the Edge Function

-- Step 1: Enable pg_cron extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Step 2: Enable http extension (for making HTTP requests)
CREATE EXTENSION IF NOT EXISTS pg_net;

-- Step 3: Grant permissions to make HTTP requests
GRANT USAGE ON SCHEMA net TO postgres, anon, authenticated, service_role;

-- Step 4: Create the cron job
-- IMPORTANT: Replace YOUR_EDGE_FUNCTION_URL with your actual Supabase Edge Function URL
-- Format: https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync

SELECT cron.schedule(
  'daily-email-sync',           -- Job name
  '0 7 * * *',                  -- Cron expression: 7:00 AM UTC = 2:00 AM EST
  $$
  SELECT
    net.http_post(
      url := 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync',
      headers := '{"Content-Type": "application/json", "Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb,
      body := '{}'::jsonb,
      timeout_milliseconds := 30000  -- 30 second timeout
    ) AS request_id;
  $$
);

-- Step 5: Verify the cron job was created
SELECT jobid, jobname, schedule, active, database 
FROM cron.job 
WHERE jobname = 'daily-email-sync';

-- ============================================
-- Additional Useful Commands
-- ============================================

-- View all cron jobs
-- SELECT * FROM cron.job;

-- View cron job execution history
-- SELECT * FROM cron.job_run_details 
-- WHERE jobid = (SELECT jobid FROM cron.job WHERE jobname = 'daily-email-sync')
-- ORDER BY start_time DESC 
-- LIMIT 10;

-- Disable the cron job
-- UPDATE cron.job SET active = false WHERE jobname = 'daily-email-sync';

-- Enable the cron job
-- UPDATE cron.job SET active = true WHERE jobname = 'daily-email-sync';

-- Delete the cron job
-- SELECT cron.unschedule('daily-email-sync');

-- Manually trigger the cron job (for testing)
-- SELECT net.http_post(
--   url := 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync',
--   headers := '{"Content-Type": "application/json", "Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb,
--   body := '{}'::jsonb
-- );

-- ============================================
-- Cron Expression Reference
-- ============================================
-- Format: minute hour day month weekday
-- 
-- Examples:
-- '0 7 * * *'    - Every day at 7:00 AM UTC (2:00 AM EST)
-- '0 */6 * * *'  - Every 6 hours
-- '0 5 * * *'    - Every day at 5:00 AM UTC (midnight EST)
-- '0 7 * * 1'    - Every Monday at 7:00 AM UTC (2:00 AM EST)
-- '*/15 * * * *' - Every 15 minutes (for testing)
-- 
-- Timezone Notes:
-- - Cron runs in UTC
-- - EST = UTC - 5 hours
-- - EDT = UTC - 4 hours (during daylight saving time)
-- - To run at 2:00 AM EST: use 7:00 AM UTC (0 7 * * *)
-- ============================================

