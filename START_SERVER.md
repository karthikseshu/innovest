# How to Start the Email-Reader API Server

## Quick Start

### 1. Kill any existing server on port 8000
```bash
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
```

### 2. Start the server
```bash
cd /Users/ranjani/Karthik/AI-Learning/email-reader
source venv/bin/activate
uvicorn src.email_parser.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Test the server (in a new terminal)
```bash
curl http://localhost:8000/api/v1/health
```

---

## Option 1: Start Without .env (Uses Defaults)

If you don't have a `.env` file configured yet:

```bash
cd /Users/ranjani/Karthik/AI-Learning/email-reader
source venv/bin/activate

# Start server (will show email connection warning, but API will work)
uvicorn src.email_parser.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
⚠️  Email connection failed on startup (this is OK if using Supabase OAuth)
INFO:     Application startup complete.
```

**Server will be running at:** `http://localhost:8000`

---

## Option 2: Start With .env (Full Configuration)

### Step 1: Create .env file

```bash
cd /Users/ranjani/Karthik/AI-Learning/email-reader
cp env.example .env
```

### Step 2: Edit .env with your actual values

```bash
nano .env
```

**Minimum required for Supabase integration:**
```bash
# Supabase (Required for batch jobs)
SUPABASE_SERVICE_ROLE_KEY=your_actual_service_role_key

# Google OAuth (Required for token refresh)
GOOGLE_CLIENT_ID=your_actual_google_client_id
GOOGLE_CLIENT_SECRET=your_actual_google_client_secret

# Batch Job Security (Optional)
BATCH_JOB_API_KEY=my-secret-key-123

# Email (Can use defaults for now)
EMAIL_HOST=gmail
EMAIL_USERNAME=dummy@gmail.com
EMAIL_PASSWORD=dummy_password
```

### Step 3: Start server

```bash
source venv/bin/activate
uvicorn src.email_parser.api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Option 3: Use Different Port

If port 8000 is already in use:

```bash
# Kill existing process on port 8000
lsof -ti:8000 | xargs kill -9

# OR use a different port
uvicorn src.email_parser.api.main:app --reload --host 0.0.0.0 --port 8001
```

---

## Troubleshooting

### Issue: "Address already in use"

**Solution 1: Kill existing server**
```bash
lsof -ti:8000 | xargs kill -9
```

**Solution 2: Use different port**
```bash
uvicorn src.email_parser.api.main:app --reload --host 0.0.0.0 --port 8001
```

### Issue: "Email connection failed"

**This is OK!** The email connection warning appears if you don't have `.env` configured, but the API will still work. The multi-account endpoints use Supabase OAuth integrations, not .env credentials.

### Issue: "No module named 'supabase'"

**Solution:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

## Verify Server is Running

```bash
# Check process
ps aux | grep uvicorn

# Check port
lsof -i:8000

# Test health endpoint
curl http://localhost:8000/api/v1/health

# View API docs
open http://localhost:8000/docs
```

---

## Recommended Startup Command

```bash
# One-liner (kills existing, starts fresh)
cd /Users/ranjani/Karthik/AI-Learning/email-reader && \
  lsof -ti:8000 | xargs kill -9 2>/dev/null || true && \
  source venv/bin/activate && \
  uvicorn src.email_parser.api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## What You'll See

### Successful Startup:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345]
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Starting Email Transaction Parser v1.0.0
⚠️       Email connection failed on startup (OK if using Supabase)
INFO:     Application startup complete.
```

### Server Ready:
```
✅ Server running on http://localhost:8000
✅ API docs available at http://localhost:8000/docs
✅ Health check: curl http://localhost:8000/api/v1/health
```

---

## Stop the Server

```bash
# Press CTRL+C in terminal where server is running
# OR
lsof -ti:8000 | xargs kill
```

---

## Summary

**Simplest command to start:**
```bash
cd /Users/ranjani/Karthik/AI-Learning/email-reader
source venv/bin/activate
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
uvicorn src.email_parser.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Server will run on:** `http://localhost:8000`  
**API docs:** `http://localhost:8000/docs`  
**Health check:** `curl http://localhost:8000/api/v1/health`

The email connection warning is normal - the batch job endpoints use Supabase OAuth instead! ✅

