# Quick Setup Guide - Render to Supabase Cron Job

## ⚡ TL;DR - 5 Minute Setup

Since your email-reader is **already deployed on Render**, you just need to:
1. Verify Render environment variables
2. Deploy Supabase Edge Function  
3. Create cron job in Supabase

---

## Step 1: Verify Render Setup (2 minutes)

### 1.1 Get Your Render URL
1. Go to https://dashboard.render.com
2. Find your email-reader service
3. Copy the URL (e.g., `https://email-reader-abc123.onrender.com`)

### 1.2 Check Environment Variables
In Render Dashboard → Your Service → Environment, verify these exist:
- ✅ `SUPABASE_URL`
- ✅ `SUPABASE_ANON_KEY`
- ✅ `SUPABASE_SERVICE_ROLE_KEY`
- ✅ `GOOGLE_CLIENT_ID`
- ✅ `GOOGLE_CLIENT_SECRET`
- ✅ `BATCH_JOB_API_KEY` ← **If missing, add it!**

**Generate BATCH_JOB_API_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and add it in Render → Environment → Add Environment Variable

### 1.3 Test Your API
```bash
# Replace with your Render URL and API key
curl -X POST "https://your-service.onrender.com/api/v1/batch/daily-sync?target_date=2025-10-18" \
  -H "X-API-Key: your_batch_job_api_key"
```

Expected: JSON response with processed transactions

---

## Step 2: Deploy Supabase Edge Function (2 minutes)

### 2.1 Install Supabase CLI (if not installed)
```bash
npm install -g supabase
```

### 2.2 Login and Link
```bash
supabase login
supabase link --project-ref YOUR_PROJECT_REF
```

Find `YOUR_PROJECT_REF` in Supabase Dashboard → Settings → General → Reference ID

### 2.3 Deploy Edge Function
```bash
cd /Users/ranjani/Karthik/AI-Learning/email-reader
supabase functions deploy daily-email-sync --no-verify-jwt
```

### 2.4 Set Secrets
```bash
# Replace with YOUR Render URL (no trailing slash)
supabase secrets set RENDER_API_URL=https://your-service.onrender.com

# Use the SAME API key from Render
supabase secrets set BATCH_JOB_API_KEY=your_batch_job_api_key
```

### 2.5 Test Edge Function
```bash
curl -X POST "https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync" \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

Get `YOUR_ANON_KEY` from Supabase Dashboard → Settings → API → anon public

---

## Step 3: Create Cron Job (1 minute)

### 3.1 Enable Extensions
In Supabase SQL Editor, run:
```sql
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;
```

### 3.2 Create Cron Job
Replace `YOUR_PROJECT_REF` and `YOUR_ANON_KEY` in this SQL, then run it:

```sql
SELECT cron.schedule(
  'daily-email-sync',
  '0 7 * * *',  -- 7:00 AM UTC = 2:00 AM EST
  $$
  SELECT
    net.http_post(
      url := 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync',
      headers := '{"Content-Type": "application/json", "Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb,
      body := '{}'::jsonb,
      timeout_milliseconds := 30000
    ) AS request_id;
  $$
);
```

### 3.3 Verify Cron Job
```sql
SELECT jobid, jobname, schedule, active 
FROM cron.job 
WHERE jobname = 'daily-email-sync';
```

Should show: `active = true`

---

## ✅ Done!

Your cron job will now run **daily at 2:00 AM EST** and:
1. Fetch all active OAuth integrations from `api.email_integrations`
2. Call your Render API for each integration
3. Process yesterday's emails
4. Insert transactions into `staging.pay_transactions`

---

## 🔍 Monitor First Run

### Option 1: Test Immediately (Recommended)
Manually trigger the Edge Function to test:
```bash
curl -X POST "https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync" \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

### Option 2: Check Tomorrow Morning
Run this SQL at 3 AM EST to verify:
```sql
-- Check cron execution
SELECT * FROM cron.job_run_details 
WHERE jobid = (SELECT jobid FROM cron.job WHERE jobname = 'daily-email-sync')
ORDER BY start_time DESC 
LIMIT 1;

-- Check inserted transactions
SELECT COUNT(*) FROM staging.pay_transactions
WHERE DATE(created_at) >= CURRENT_DATE - 1;
```

---

## 🆘 Troubleshooting

### Cron job not running?
```sql
UPDATE cron.job SET active = true WHERE jobname = 'daily-email-sync';
```

### No transactions inserted?
1. Check Render API is responding (test curl command above)
2. Check Edge Function logs in Supabase Dashboard
3. Verify `api.email_integrations` has active OAuth records

### Render service spinning down (Free tier)?
Consider upgrading to Render Starter ($7/month) for always-on service, or the Edge Function will wake it up (30-60 second delay).

---

## 📚 Need More Details?

- **Full Guide**: See `DEPLOYMENT_CHECKLIST.md`
- **Render Specific**: See `RENDER_DEPLOYMENT.md`
- **Cron Details**: See `SUPABASE_CRON_SETUP.md`
- **Quick Commands**: See `QUICK_REFERENCE.md`

---

## 🎉 That's It!

You now have a fully automated email processing system! 🚀

**Cost**: $0 additional (unless upgrading Render plan)  
**Maintenance**: Minimal - just monitor first few runs

---

## Key URLs to Save

- **Render Dashboard**: https://dashboard.render.com
- **Render API**: `https://your-service.onrender.com`
- **Supabase Dashboard**: `https://supabase.com/dashboard/project/YOUR_PROJECT_REF`
- **Edge Function**: `https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync`

**Git Snapshot**: Commit `065567d` - "Update documentation: Replace Vercel with Render"

