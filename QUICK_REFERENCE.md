# Quick Reference - Email Reader Cron Job

## 🚀 Quick Commands

### Deploy to Vercel
```bash
vercel --prod
```

### Deploy Edge Function
```bash
cd /Users/ranjani/Karthik/AI-Learning/email-reader
supabase functions deploy daily-email-sync --no-verify-jwt
```

### Test API Locally
```bash
make run
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync?target_date=2025-10-18" \
  -H "X-API-Key: your_batch_job_api_key"
```

### Test Vercel API
```bash
curl -X POST "https://your-app.vercel.app/api/v1/batch/daily-sync?target_date=2025-10-18" \
  -H "X-API-Key: your_batch_job_api_key"
```

### Test Edge Function
```bash
curl -X POST "https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync" \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

---

## 📊 Monitoring Queries

### Check Cron Job Status
```sql
SELECT jobid, jobname, schedule, active 
FROM cron.job 
WHERE jobname = 'daily-email-sync';
```

### Check Last 5 Executions
```sql
SELECT * FROM cron.job_run_details 
WHERE jobid = (SELECT jobid FROM cron.job WHERE jobname = 'daily-email-sync')
ORDER BY start_time DESC 
LIMIT 5;
```

### Check Today's Transactions
```sql
SELECT 
  COUNT(*) as total_transactions,
  SUM(amount_paid) as total_amount,
  COUNT(DISTINCT user_id) as unique_users
FROM staging.pay_transactions
WHERE DATE(created_at) = CURRENT_DATE;
```

### Check Recent Transactions
```sql
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

---

## 🔧 Cron Job Management

### Disable Cron Job
```sql
UPDATE cron.job SET active = false WHERE jobname = 'daily-email-sync';
```

### Enable Cron Job
```sql
UPDATE cron.job SET active = true WHERE jobname = 'daily-email-sync';
```

### Delete Cron Job
```sql
SELECT cron.unschedule('daily-email-sync');
```

### Manually Trigger Edge Function
```bash
curl -X POST "https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json"
```

---

## 📝 Environment Variables

### Vercel
```
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
BATCH_JOB_API_KEY
```

### Supabase Edge Function
```
VERCEL_API_URL
BATCH_JOB_API_KEY
```

---

## 🕐 Cron Schedule Reference

| Schedule | Description |
|----------|-------------|
| `0 7 * * *` | 7:00 AM UTC (2:00 AM EST) - **Current** |
| `0 8 * * *` | 8:00 AM UTC (3:00 AM EST) |
| `0 */6 * * *` | Every 6 hours |
| `*/15 * * * *` | Every 15 minutes (testing) |
| `0 7 * * 1` | Every Monday at 2 AM EST |

**Note**: Cron runs in UTC. EST = UTC - 5 hours

---

## 🔍 Troubleshooting

### No transactions inserted?
1. Check `api.email_integrations` for active OAuth records
2. Verify emails exist in Gmail for the target date
3. Check Vercel API logs
4. Check Edge Function logs

### Cron job not running?
```sql
-- Check if active
SELECT active FROM cron.job WHERE jobname = 'daily-email-sync';

-- Enable if disabled
UPDATE cron.job SET active = true WHERE jobname = 'daily-email-sync';
```

### API returning 401 Unauthorized?
- Verify `BATCH_JOB_API_KEY` matches in Vercel and Supabase
- Check `X-API-Key` header is being sent

### Duplicate transactions?
```sql
-- Find duplicates
SELECT transaction_number, COUNT(*) 
FROM staging.pay_transactions 
GROUP BY transaction_number, user_id
HAVING COUNT(*) > 1;
```

---

## 📂 Important Files

| File | Purpose |
|------|---------|
| `SUPABASE_CRON_SETUP.md` | Detailed cron setup guide |
| `VERCEL_DEPLOYMENT.md` | Vercel deployment guide |
| `DEPLOYMENT_CHECKLIST.md` | Step-by-step deployment checklist |
| `setup_cron_job.sql` | SQL to create cron job |
| `supabase/functions/daily-email-sync/index.ts` | Edge Function code |
| `vercel.json` | Vercel configuration |

---

## 🔗 Important URLs

- **Vercel Dashboard**: https://vercel.com/dashboard
- **Supabase Dashboard**: https://supabase.com/dashboard
- **Vercel App**: `https://your-app.vercel.app`
- **Edge Function**: `https://YOUR_PROJECT_REF.supabase.co/functions/v1/daily-email-sync`

---

## 💡 Tips

1. **Test First**: Always test manually before relying on cron
2. **Monitor Daily**: Check logs for the first week
3. **Backup Data**: Export `staging.pay_transactions` regularly
4. **Rotate Keys**: Change `BATCH_JOB_API_KEY` periodically
5. **Check Quotas**: Monitor Vercel and Gmail API usage

---

## 🆘 Emergency Contacts

- Vercel Support: https://vercel.com/support
- Supabase Support: https://supabase.com/support
- Gmail API Status: https://www.google.com/appsstatus

---

## 📅 Maintenance Schedule

- **Daily**: Check cron execution logs
- **Weekly**: Review transaction counts
- **Monthly**: Check API usage and costs
- **Quarterly**: Rotate API keys
- **Annually**: Review and optimize code

---

## 🎯 Key Metrics to Track

1. **Transactions Processed**: Daily count
2. **Execution Time**: How long each run takes
3. **Error Rate**: Failed transactions / Total
4. **API Usage**: Vercel function invocations
5. **Gmail API Quota**: Requests used / Available

---

## ✅ Health Check Indicators

| Indicator | Healthy | Action Required |
|-----------|---------|-----------------|
| Cron Status | Active = true | Enable if false |
| Last Run | < 24 hours ago | Check logs if older |
| Transactions | > 0 per day | Verify OAuth integrations |
| Errors | 0 | Review logs if > 0 |
| API Response | 200 OK | Check Vercel if not |

---

**Last Updated**: [Current Date]
**Version**: 1.0

