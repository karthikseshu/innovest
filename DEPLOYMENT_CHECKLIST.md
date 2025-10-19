# Deployment Checklist - Email Reader Cron Job

Use this checklist to deploy the email-reader API and set up the daily cron job.

## ✅ Pre-Deployment Checklist

### 1. Verify Local Setup Works
- [ ] Code snapshot created (commit: `Working state: All 3 transactions parsing and inserting correctly`)
- [ ] Local API server runs without errors (`make run`)
- [ ] Test endpoint works locally:
  ```bash
  curl -X POST "http://localhost:8000/api/v1/batch/daily-sync?target_date=2025-10-18" \
    -H "X-API-Key: your_batch_job_api_key"
  ```
- [ ] Transactions are inserted into `staging.pay_transactions`

### 2. Prepare Environment Variables
- [ ] `SUPABASE_URL` - Copy from Supabase Dashboard → Settings → API
- [ ] `SUPABASE_ANON_KEY` - Copy from Supabase Dashboard → Settings → API
- [ ] `SUPABASE_SERVICE_ROLE_KEY` - Copy from Supabase Dashboard → Settings → API (Keep secret!)
- [ ] `GOOGLE_CLIENT_ID` - From Google Cloud Console
- [ ] `GOOGLE_CLIENT_SECRET` - From Google Cloud Console
- [ ] `BATCH_JOB_API_KEY` - Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### 3. Database Setup
- [ ] `staging` schema exists in Supabase
- [ ] `staging.pay_transactions` table created (run `create_pay_transactions_table.sql`)
- [ ] `api.email_integrations` table has OAuth records with `is_active = true`
- [ ] Permissions granted (run `fix_staging_schema_permissions.sql`)
- [ ] `staging` schema exposed in PostgREST (Supabase Dashboard → Settings → API → Exposed schemas)

---

## 🚀 Deployment Steps

### Phase 1: Verify Render Deployment

#### Step 1: Find Your Render Service URL
- [ ] Go to https://dashboard.render.com
- [ ] Find your email-reader service
- [ ] Copy the service URL (e.g., `https://email-reader-xxx.onrender.com`)

#### Step 2: Verify Environment Variables
In Render Dashboard → Your Service → Environment, ensure these are set:

- [ ] `SUPABASE_URL`
- [ ] `SUPABASE_ANON_KEY`
- [ ] `SUPABASE_SERVICE_ROLE_KEY`
- [ ] `GOOGLE_CLIENT_ID`
- [ ] `GOOGLE_CLIENT_SECRET`
- [ ] `BATCH_JOB_API_KEY`

**Note**: If `BATCH_JOB_API_KEY` is missing, generate one:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
Then add it in Render Dashboard → Environment → Add Environment Variable

#### Step 3: Redeploy (if environment variables were added)
- [ ] Click "Manual Deploy" → "Deploy latest commit" (only if you added new env vars)
- [ ] Wait for deployment to complete (~2-3 minutes)

#### Step 4: Test Render Deployment
```bash
# Test health endpoint
curl https://your-service-name.onrender.com/

# Test batch endpoint
curl -X POST "https://your-service-name.onrender.com/api/v1/batch/daily-sync?target_date=2025-10-18" \
  -H "X-API-Key: your_batch_job_api_key"
```

- [ ] Health endpoint returns 200 OK
- [ ] Batch endpoint processes emails successfully
- [ ] Check Render logs for any errors (Dashboard → Logs tab)

---

### Phase 2: Set Up Supabase Edge Function

#### Step 1: Install Supabase CLI
```bash
npm install -g supabase
```
- [ ] Supabase CLI installed

#### Step 2: Login and Link Project
```bash
supabase login
supabase link --project-ref YOUR_PROJECT_REF
```
- [ ] Logged in to Supabase CLI
- [ ] Project linked (find project ref in Supabase Dashboard → Settings → General)

#### Step 3: Deploy Edge Function
```bash
cd /Users/ranjani/Karthik/AI-Learning/email-reader
supabase functions deploy daily-email-sync --no-verify-jwt
```
- [ ] Edge function deployed successfully
- [ ] Note the function URL (e.g., `https://xxx.supabase.co/functions/v1/daily-email-sync`)

#### Step 4: Set Edge Function Secrets
```bash
supabase secrets set RENDER_API_URL=https://your-service-name.onrender.com
supabase secrets set BATCH_JOB_API_KEY=your_batch_job_api_key
```
- [ ] `RENDER_API_URL` secret set (use your Render service URL)
- [ ] `BATCH_JOB_API_KEY` secret set (same key as in Render)

#### Step 5: Test Edge Function
```bash
curl -X POST "https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```
- [ ] Edge function returns success
- [ ] Check Edge Function logs in Supabase Dashboard
- [ ] Verify transactions inserted into `staging.pay_transactions`

---

### Phase 3: Set Up Cron Job

#### Step 1: Enable Extensions
Run in Supabase SQL Editor:
```sql
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;
```
- [ ] `pg_cron` extension enabled
- [ ] `pg_net` extension enabled

#### Step 2: Create Cron Job
Edit `setup_cron_job.sql` to replace:
- `YOUR_PROJECT_REF` with your Supabase project reference
- `YOUR_ANON_KEY` with your Supabase anon key

Run the entire `setup_cron_job.sql` file in Supabase SQL Editor.

- [ ] Cron job created successfully
- [ ] Verify with: `SELECT * FROM cron.job WHERE jobname = 'daily-email-sync';`

#### Step 3: Test Cron Job (Optional)
Create a test cron that runs every minute:
```sql
SELECT cron.schedule(
  'test-email-sync',
  '* * * * *',
  $$
  SELECT
    net.http_post(
      url := 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync',
      headers := '{"Content-Type": "application/json", "Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb,
      body := '{}'::jsonb
    ) AS request_id;
  $$
);
```
- [ ] Test cron created
- [ ] Wait 1-2 minutes and check execution: `SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 5;`
- [ ] Verify transactions inserted
- [ ] Delete test cron: `SELECT cron.unschedule('test-email-sync');`

---

## 📊 Post-Deployment Verification

### Check All Components

#### 1. Render API
- [ ] Visit: `https://your-service-name.onrender.com/`
- [ ] Returns: `{"message": "Email Transaction Parser API", "version": "1.0.0", "status": "running"}`

#### 2. Supabase Edge Function
- [ ] Check logs in Supabase Dashboard → Edge Functions → daily-email-sync
- [ ] No errors visible
- [ ] Test execution successful

#### 3. Cron Job
```sql
-- Check cron job exists and is active
SELECT jobid, jobname, schedule, active 
FROM cron.job 
WHERE jobname = 'daily-email-sync';

-- Check last execution
SELECT * FROM cron.job_run_details 
WHERE jobid = (SELECT jobid FROM cron.job WHERE jobname = 'daily-email-sync')
ORDER BY start_time DESC 
LIMIT 1;
```
- [ ] Cron job is active
- [ ] Schedule is correct: `0 7 * * *` (2 AM EST)

#### 4. Database
```sql
-- Check transactions in staging
SELECT 
  id,
  user_id,
  amount_paid,
  paid_by,
  paid_to,
  transaction_number,
  transaction_date,
  created_at
FROM staging.pay_transactions
ORDER BY created_at DESC
LIMIT 10;
```
- [ ] Transactions are being inserted
- [ ] Data looks correct
- [ ] No duplicate transaction numbers for same user

---

## 🔍 Monitoring Setup

### Daily Checks (First Week)

- [ ] **Day 1**: Check at 3 AM EST - verify cron ran at 2 AM
  ```sql
  SELECT * FROM cron.job_run_details 
  WHERE jobid = (SELECT jobid FROM cron.job WHERE jobname = 'daily-email-sync')
  AND start_time > NOW() - INTERVAL '24 hours'
  ORDER BY start_time DESC;
  ```

- [ ] **Day 2-7**: Repeat daily check
- [ ] Check Vercel function usage (Dashboard → Usage)
- [ ] Check for any error patterns

### Set Up Alerts (Optional)

1. **Vercel**:
   - Enable email notifications for deployment failures
   - Settings → Notifications

2. **Supabase**:
   - Monitor Edge Function errors
   - Set up webhook for failures (if available in your plan)

---

## 🔧 Troubleshooting Guide

### Issue: Cron job not running

**Check:**
```sql
SELECT * FROM cron.job WHERE jobname = 'daily-email-sync';
```

**If `active = false`:**
```sql
UPDATE cron.job SET active = true WHERE jobname = 'daily-email-sync';
```

### Issue: Edge Function timeout

**Solution**: Increase timeout in Edge Function or optimize API response time

### Issue: No transactions inserted

**Check:**
1. Vercel API logs
2. Edge Function logs
3. `api.email_integrations` - verify OAuth records exist
4. Test manual API call

### Issue: Duplicate transactions

**Check:**
```sql
SELECT transaction_number, COUNT(*) 
FROM staging.pay_transactions 
GROUP BY transaction_number 
HAVING COUNT(*) > 1;
```

**Solution**: Transaction numbers should be unique. Check parser logic.

---

## 📝 Important URLs to Save

- [ ] **Vercel App**: `https://your-app.vercel.app`
- [ ] **Edge Function**: `https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync`
- [ ] **Supabase Dashboard**: `https://supabase.com/dashboard/project/YOUR_PROJECT_REF`
- [ ] **GitHub Repo**: `https://github.com/your-username/email-reader`

---

## 🎉 Success Criteria

All boxes checked means successful deployment:

- [ ] ✅ Vercel API is live and accessible
- [ ] ✅ Edge Function deployed and working
- [ ] ✅ Cron job scheduled and active
- [ ] ✅ Test run completed successfully
- [ ] ✅ Transactions inserted into `staging.pay_transactions`
- [ ] ✅ No errors in logs
- [ ] ✅ API key authentication working
- [ ] ✅ Monitoring set up

---

## 📞 Support

If you encounter issues:
1. Check this checklist again
2. Review logs (Vercel + Supabase)
3. Test components individually
4. Verify environment variables

## Next Steps After Deployment

- [ ] Monitor first 3 days of automated runs
- [ ] Set up backup/export strategy for `staging.pay_transactions`
- [ ] Document any custom configurations
- [ ] Create runbook for common operations
- [ ] Plan for scaling if needed

---

**Deployment Date**: _________________

**Deployed By**: _________________

**Vercel URL**: _________________

**Notes**: 
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

