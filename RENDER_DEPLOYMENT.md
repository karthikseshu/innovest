# Render Deployment Guide for Email-Reader API

## ✅ Already Deployed!

Your email-reader API is already deployed on Render. This guide helps you verify and update the deployment if needed.

## Current Deployment

- **Platform**: Render
- **URL**: Check your Render Dashboard for the deployment URL
  - Format: `https://your-service-name.onrender.com`

## Verify Deployment

### 1. Check Health Endpoint

```bash
curl https://your-service-name.onrender.com/
```

Expected response:
```json
{
  "message": "Email Transaction Parser API",
  "version": "1.0.0",
  "status": "running"
}
```

### 2. Test Batch Endpoint

```bash
curl -X POST "https://your-service-name.onrender.com/api/v1/batch/daily-sync?target_date=2025-10-18" \
  -H "X-API-Key: your_batch_job_api_key" \
  -H "Content-Type: application/json"
```

## Environment Variables

Ensure these are set in Render Dashboard → Your Service → Environment:

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | ✅ |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | ✅ |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | ✅ |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | ✅ |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | ✅ |
| `BATCH_JOB_API_KEY` | API key for batch job auth | ✅ |
| `DATABASE_URL` | SQLite database URL | ⚠️ Optional (for local testing) |

### Add/Update Environment Variables

1. Go to Render Dashboard: https://dashboard.render.com
2. Select your service
3. Go to "Environment" tab
4. Add or update variables
5. Click "Save Changes" (will trigger redeploy)

### Generate BATCH_JOB_API_KEY (if not set)

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Update Deployment

### Automatic Deployment (Git Push)

Render auto-deploys when you push to your connected branch:

```bash
git push origin main
```

### Manual Deployment

In Render Dashboard:
1. Go to your service
2. Click "Manual Deploy" → "Deploy latest commit"

### View Deployment Logs

```bash
# In Render Dashboard
Your Service → Logs tab
```

Or use Render CLI:
```bash
render logs --service your-service-name
```

## Render Configuration

Your service should have these settings:

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn src.email_parser.api.main:app --host 0.0.0.0 --port $PORT`
- **Python Version**: 3.11
- **Plan**: Free or Starter (recommended)

### Check Configuration

In Render Dashboard → Your Service → Settings:
- ✅ Build Command is correct
- ✅ Start Command is correct
- ✅ Branch is correct (usually `main` or `master`)
- ✅ Auto-Deploy is enabled (if desired)

## Important Notes

### Render Free Tier
- ⚠️ **Services spin down after 15 minutes of inactivity**
- ⚠️ **Cold starts take 30-60 seconds**
- ✅ **750 hours/month free** (enough for 24/7)

### For Production Use
- **Recommended**: Upgrade to **Starter plan ($7/month)**
  - No spin-down
  - Faster response times
  - Better for cron jobs

### Keep Service Alive (Free Tier)
If using free tier, you can ping the service regularly:

```sql
-- Add this to your cron job to keep service warm
SELECT net.http_get(
  url := 'https://your-service-name.onrender.com/'
) AS request_id;
```

But **Starter plan is recommended** for reliable cron jobs.

## Get Your Render Service URL

### Option 1: Render Dashboard
1. Go to https://dashboard.render.com
2. Click on your service
3. Copy the URL shown at the top (e.g., `https://email-reader-xxx.onrender.com`)

### Option 2: Render CLI
```bash
render services list
```

## Troubleshooting

### Service Not Responding
- Check Render Dashboard → Logs for errors
- Verify environment variables are set
- Check if service is running (free tier may have spun down)

### Environment Variables Not Working
- Click "Save Changes" in Environment tab (triggers redeploy)
- Check spelling of variable names
- Restart service manually

### Build Failed
- Check `requirements.txt` includes all dependencies
- Verify Python version (should be 3.11)
- Check build logs in Render Dashboard

## Monitoring

### Check Service Health
```bash
# Health check
curl https://your-service-name.onrender.com/

# Check specific endpoint
curl -X POST "https://your-service-name.onrender.com/api/v1/batch/daily-sync?target_date=2025-10-18" \
  -H "X-API-Key: your_batch_job_api_key"
```

### View Logs
Render Dashboard → Your Service → Logs

## Cost

### Free Tier
- ✅ 750 hours/month
- ⚠️ Spins down after 15 minutes inactivity
- ⚠️ 30-60 second cold start

### Starter Plan ($7/month) - **Recommended for Cron**
- ✅ Always on (no spin down)
- ✅ Fast response times
- ✅ Reliable for scheduled jobs

## Next Steps

1. ✅ Verify your Render service URL
2. ✅ Ensure all environment variables are set (especially `BATCH_JOB_API_KEY`)
3. ✅ Test the batch endpoint manually
4. ✅ Update Supabase Edge Function with your Render URL
5. ✅ Set up Supabase cron job

## Support

- **Render Docs**: https://render.com/docs
- **Render Community**: https://community.render.com
- **Render Status**: https://status.render.com

