# Vercel Deployment Guide for Email-Reader API

This guide explains how to deploy the email-reader API to Vercel.

## Prerequisites

1. ✅ Vercel account (free tier works)
2. ✅ GitHub repository with the code
3. ✅ All environment variables ready

## Deployment Steps

### Option 1: Deploy via Vercel Dashboard (Recommended)

1. **Go to Vercel Dashboard**: https://vercel.com/dashboard

2. **Import Project**:
   - Click "Add New..." → "Project"
   - Select your GitHub repository
   - Configure project settings

3. **Configure Build Settings**:
   - **Framework Preset**: Other
   - **Build Command**: `pip install -r requirements.txt`
   - **Output Directory**: Leave empty
   - **Install Command**: Leave default

4. **Add Environment Variables**:
   ```
   DATABASE_URL=sqlite:///./transactions.db
   EMAIL_SERVER=imap.gmail.com
   EMAIL_PORT=993
   EMAIL_USERNAME=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password
   SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
   SUPABASE_ANON_KEY=your_anon_key
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   BATCH_JOB_API_KEY=your_secure_api_key_here
   ```

5. **Deploy**: Click "Deploy"

### Option 2: Deploy via Vercel CLI

1. **Install Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**:
   ```bash
   vercel login
   ```

3. **Deploy**:
   ```bash
   cd /Users/ranjani/Karthik/AI-Learning/email-reader
   vercel
   ```

4. **Follow the prompts**:
   - Link to existing project or create new
   - Choose production deployment

5. **Set environment variables** (one-time setup):
   ```bash
   vercel env add DATABASE_URL
   vercel env add SUPABASE_URL
   vercel env add SUPABASE_ANON_KEY
   vercel env add SUPABASE_SERVICE_ROLE_KEY
   vercel env add GOOGLE_CLIENT_ID
   vercel env add GOOGLE_CLIENT_SECRET
   vercel env add BATCH_JOB_API_KEY
   ```

6. **Redeploy** after adding environment variables:
   ```bash
   vercel --prod
   ```

## Vercel Configuration

Create a `vercel.json` file in the project root (already exists):

```json
{
  "version": 2,
  "builds": [
    {
      "src": "src/email_parser/api/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "src/email_parser/api/main.py"
    }
  ],
  "env": {
    "PYTHON_VERSION": "3.11"
  }
}
```

## Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Your Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | `eyJhbG...` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (keep secret!) | `eyJhbG...` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | `xxx.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | `GOCSPX-xxx` |
| `BATCH_JOB_API_KEY` | API key for batch job authentication | Generate a strong random key |
| `DATABASE_URL` | SQLite database URL (for local testing only) | `sqlite:///./transactions.db` |

### Generate BATCH_JOB_API_KEY

```bash
# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Using OpenSSL
openssl rand -base64 32
```

## Testing the Deployment

### 1. Test Health Endpoint

```bash
curl https://your-app.vercel.app/
```

Expected response:
```json
{
  "message": "Email Transaction Parser API",
  "version": "1.0.0",
  "status": "running"
}
```

### 2. Test Batch Endpoint (with API Key)

```bash
curl -X POST "https://your-app.vercel.app/api/v1/batch/daily-sync?target_date=2025-10-18" \
  -H "X-API-Key: your_batch_job_api_key" \
  -H "Content-Type: application/json"
```

### 3. Check Logs

View logs in Vercel Dashboard:
- Go to your project
- Click "Deployments"
- Click on the latest deployment
- Click "Functions" tab to see logs

## Troubleshooting

### Issue: Module not found

**Solution**: Make sure `requirements.txt` includes all dependencies:
```bash
pip freeze > requirements.txt
```

### Issue: Import errors

**Solution**: Check that your Python version matches (3.11):
```json
{
  "env": {
    "PYTHON_VERSION": "3.11"
  }
}
```

### Issue: Environment variables not working

**Solution**: 
1. Add them in Vercel Dashboard → Settings → Environment Variables
2. Redeploy after adding variables

### Issue: Function timeout

**Solution**: Vercel free tier has 10-second timeout. Upgrade to Pro for 60 seconds or optimize your code.

## Monitoring

### View Deployment Status

```bash
vercel ls
```

### View Function Logs

```bash
vercel logs your-deployment-url
```

### View Function Analytics

Vercel Dashboard → Your Project → Analytics

## Custom Domain (Optional)

1. Go to Vercel Dashboard → Your Project → Settings → Domains
2. Add your custom domain
3. Update DNS records as instructed
4. Wait for DNS propagation (can take up to 48 hours)

## Continuous Deployment

Vercel automatically deploys:
- **Production**: When you push to `main` branch
- **Preview**: When you create a pull request

Configure in Vercel Dashboard → Settings → Git

## Cost

- **Free Tier**: 
  - 100 GB bandwidth/month
  - 100 hours serverless function execution
  - 12 concurrent builds
  - **Perfect for this use case** (runs once per day)

- **Pro Tier** ($20/month):
  - 1 TB bandwidth
  - 1000 hours execution
  - 60-second function timeout (vs 10 seconds on free)

## Security Best Practices

1. ✅ Never commit `.env` file to Git
2. ✅ Use environment variables for all secrets
3. ✅ Rotate `BATCH_JOB_API_KEY` periodically
4. ✅ Keep `SUPABASE_SERVICE_ROLE_KEY` secret (never expose to client)
5. ✅ Use HTTPS only (Vercel provides this automatically)

## Next Steps

After deployment:
1. ✅ Copy your Vercel deployment URL
2. ✅ Update Supabase Edge Function with the URL
3. ✅ Set up Supabase cron job
4. ✅ Test the entire flow
5. ✅ Monitor the first few runs

## Support

If you encounter issues:
1. Check Vercel function logs
2. Check Supabase logs
3. Test endpoints manually with curl
4. Verify all environment variables are set correctly

