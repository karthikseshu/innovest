// Supabase Edge Function: daily-email-sync
// Triggers the email-reader API to sync transactions from the previous day

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface SyncResponse {
  success: boolean;
  message: string;
  processed_emails?: number;
  inserted_count?: number;
  duplicate_count?: number;
  error_count?: number;
  target_date?: string;
  error?: string;
}

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    console.log('🚀 Starting daily email sync...');

    // Get environment variables
    const RENDER_API_URL = Deno.env.get('RENDER_API_URL');
    const BATCH_JOB_API_KEY = Deno.env.get('BATCH_JOB_API_KEY');

    if (!RENDER_API_URL || !BATCH_JOB_API_KEY) {
      throw new Error('Missing required environment variables: RENDER_API_URL or BATCH_JOB_API_KEY');
    }

    // Calculate yesterday's date in YYYY-MM-DD format
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const targetDate = yesterday.toISOString().split('T')[0]; // Format: YYYY-MM-DD

    console.log(`📅 Target date: ${targetDate}`);

    // Call the email-reader API on Render
    const apiUrl = `${RENDER_API_URL}/api/v1/batch/daily-sync?target_date=${targetDate}`;
    console.log(`🔗 Calling Render API: ${apiUrl}`);

    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': BATCH_JOB_API_KEY,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`❌ API call failed: ${response.status} ${response.statusText}`);
      console.error(`Error response: ${errorText}`);
      
      throw new Error(`API call failed: ${response.status} ${response.statusText} - ${errorText}`);
    }

    const data: SyncResponse = await response.json();
    console.log('✅ API response:', JSON.stringify(data, null, 2));

    // Return success response
    return new Response(
      JSON.stringify({
        success: true,
        message: 'Daily email sync completed successfully',
        target_date: targetDate,
        api_response: data,
        timestamp: new Date().toISOString(),
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
      }
    );

  } catch (error) {
    console.error('❌ Error in daily-email-sync:', error);

    return new Response(
      JSON.stringify({
        success: false,
        error: error.message,
        timestamp: new Date().toISOString(),
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 500,
      }
    );
  }
});

/* Example cron job setup in Supabase SQL Editor:

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;

-- Schedule daily sync at 2:00 AM EST (7:00 AM UTC)
SELECT cron.schedule(
  'daily-email-sync',
  '0 7 * * *',
  $$
  SELECT
    net.http_post(
      url := 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync',
      headers := '{"Content-Type": "application/json", "Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb,
      body := '{}'::jsonb
    ) AS request_id;
  $$
);

-- View cron jobs
SELECT * FROM cron.job;

-- View cron job history
SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 10;

*/

