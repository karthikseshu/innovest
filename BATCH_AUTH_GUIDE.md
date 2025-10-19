# Batch Job Authentication Guide

## Overview

Batch job endpoints support **optional API key authentication** to prevent unauthorized access.

## Authentication Options

### Option 1: No Authentication (Default)

**Configuration:**
```bash
# Don't set BATCH_JOB_API_KEY in .env
# Or leave it empty
BATCH_JOB_API_KEY=
```

**Usage:**
```bash
# No header required
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync"
```

**Use case:** Development, internal network, trusted environment

---

### Option 2: API Key Authentication (Recommended for Production) ✅

**Configuration:**
```bash
# In .env file
BATCH_JOB_API_KEY=my-secret-batch-key-12345
```

**Usage:**
```bash
# Add X-API-Key header
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync" \
  -H "X-API-Key: my-secret-batch-key-12345"
```

**Use case:** Production, public-facing API, scheduled jobs

---

## Setup Instructions

### Step 1: Generate a Secure API Key

```bash
# Generate a random API key
openssl rand -hex 32
# Output: a7f3c2d8e9b1f4a6c5d8e7f9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1
```

### Step 2: Add to .env File

```bash
# email-reader/.env
BATCH_JOB_API_KEY=a7f3c2d8e9b1f4a6c5d8e7f9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1
```

### Step 3: Restart the Application

```bash
# Restart to load new config
make run
```

### Step 4: Test Authentication

**Without API key (should fail):**
```bash
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync"
```

**Response:**
```json
{
  "detail": "API key required. Provide X-API-Key header."
}
```

**With API key (should succeed):**
```bash
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync" \
  -H "X-API-Key: a7f3c2d8e9b1f4a6c5d8e7f9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1"
```

**Response:**
```json
{
  "batch_job": "daily-sync",
  "integrations_processed": 3,
  "total_inserted_to_supabase": 25,
  "message": "Daily batch complete: Processed 25 transactions..."
}
```

---

## Protected Endpoints

All `/batch/*` endpoints require API key authentication (if configured):

| Endpoint | Requires X-API-Key? |
|----------|-------------------|
| `POST /api/v1/batch/daily-sync` | ✅ Yes (if configured) |
| `POST /api/v1/batch/sync-and-store/sender/{email}` | ✅ Yes (if configured) |
| `POST /api/v1/batch/sync-and-store/sender/{email}/date-range` | ✅ Yes (if configured) |
| `POST /api/v1/sync/sender/{email}` | ❌ No (read-only endpoint) |

---

## Cron Job with Authentication

### Shell Script with API Key

```bash
#!/bin/bash
# batch-job.sh

API_KEY="a7f3c2d8e9b1f4a6c5d8e7f9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1"
API_URL="http://localhost:8000/api/v1/batch/daily-sync"

# Call batch endpoint with API key
curl -X POST "$API_URL" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  >> /var/log/email-batch.log 2>&1

# Check exit code
if [ $? -eq 0 ]; then
  echo "$(date): Batch job completed successfully" >> /var/log/email-batch.log
else
  echo "$(date): Batch job failed" >> /var/log/email-batch.log
fi
```

### Cron Job

```cron
# Daily at 2 AM
0 2 * * * /path/to/batch-job.sh
```

---

## Environment Variable Storage

### Development (.env file)

```bash
# email-reader/.env
BATCH_JOB_API_KEY=my-dev-key-12345
```

### Production (Environment Variables)

**Docker:**
```bash
docker run -e BATCH_JOB_API_KEY=prod-key-xyz your-image
```

**Systemd:**
```ini
[Service]
Environment="BATCH_JOB_API_KEY=prod-key-xyz"
```

**Kubernetes:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: email-reader-secrets
data:
  BATCH_JOB_API_KEY: base64-encoded-key
```

---

## Security Best Practices

### ✅ Do

1. **Use strong random keys**: 32+ characters, hex or base64
2. **Store securely**: Use secret managers (AWS Secrets Manager, Vault, etc.)
3. **Rotate regularly**: Change API key every 90 days
4. **Use HTTPS**: Always use TLS in production
5. **Monitor access**: Log all batch job calls

### ❌ Don't

1. **Don't commit to git**: Add `.env` to `.gitignore`
2. **Don't share publicly**: Keep API key secret
3. **Don't use simple keys**: Avoid "password123"
4. **Don't hardcode**: Use environment variables
5. **Don't reuse**: Use different keys for dev/staging/prod

---

## Testing

### Test Without API Key

```bash
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync"
```

**Expected (if BATCH_JOB_API_KEY is set):**
```json
{
  "detail": "API key required. Provide X-API-Key header."
}
```

### Test With Invalid API Key

```bash
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync" \
  -H "X-API-Key: wrong-key"
```

**Expected:**
```json
{
  "detail": "Invalid API key"
}
```

### Test With Valid API Key

```bash
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync" \
  -H "X-API-Key: your-correct-api-key"
```

**Expected:**
```json
{
  "batch_job": "daily-sync",
  "integrations_processed": 3,
  "total_inserted_to_supabase": 25,
  "message": "Daily batch complete..."
}
```

---

## Monitoring & Logging

### Log Successful Batch Jobs

```bash
# Application logs
2025-10-18 02:00:00 - INFO - Processing daily batch for 3 OAuth integrations
2025-10-18 02:00:15 - INFO - Successfully inserted 25 transactions to Supabase
2025-10-18 02:00:15 - INFO - Daily batch job complete
```

### Alert on Failures

```bash
# Monitor for errors
tail -f /var/log/email-batch.log | grep -i "error\|failed"
```

---

## Answer to Your Question

### Q: "Do I have to add any auth in header?"

### A: **It Depends on Your Configuration**

#### If `BATCH_JOB_API_KEY` is NOT set in .env:

```bash
# No header needed
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync"
```

#### If `BATCH_JOB_API_KEY` IS set in .env (Recommended):

```bash
# X-API-Key header required
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync" \
  -H "X-API-Key: your-api-key-from-env"
```

---

## Recommended Production Setup

### .env Configuration

```bash
# Required for Supabase
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Recommended for security
BATCH_JOB_API_KEY=a7f3c2d8e9b1f4a6c5d8e7f9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1
```

### Cron Job with Authentication

```bash
#!/bin/bash
# /opt/email-reader/batch-job.sh

# Load API key from secure location
API_KEY=$(cat /etc/email-reader/api-key.txt)

# Run batch job
curl -X POST "http://localhost:8000/api/v1/batch/daily-sync" \
  -H "X-API-Key: $API_KEY" \
  >> /var/log/email-batch.log 2>&1
```

```cron
# Daily at 2 AM
0 2 * * * /opt/email-reader/batch-job.sh
```

---

## Summary

✅ **Authentication is OPTIONAL**
- Without `BATCH_JOB_API_KEY` → No auth needed
- With `BATCH_JOB_API_KEY` → X-API-Key header required

✅ **For Production: Use API Key**
```bash
curl -H "X-API-Key: your-key" http://api.com/api/v1/batch/daily-sync
```

✅ **For Development: Skip Auth**
```bash
# Don't set BATCH_JOB_API_KEY
curl http://localhost:8000/api/v1/batch/daily-sync
```

**Recommended: Set `BATCH_JOB_API_KEY` for production security!** 🔒

