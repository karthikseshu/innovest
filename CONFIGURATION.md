# Email Configuration Guide

This guide shows how to configure the email parser for different email providers.

## Quick Configuration

Copy `env.example` to `.env` and update the values:

```bash
cp env.example .env
```

## Email Provider Configurations

### 1. Gmail

```env
EMAIL_HOST=gmail
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_PORT=993
EMAIL_USE_SSL=true
```

**Note**: For Gmail, you need to:
1. Enable 2-factor authentication
2. Generate an "App Password" (not your regular password)
3. Use the app password in `EMAIL_PASSWORD`

### 2. Outlook/Hotmail

```env
EMAIL_HOST=outlook
EMAIL_USERNAME=your_email@outlook.com
EMAIL_PASSWORD=your_password
EMAIL_PORT=993
EMAIL_USE_SSL=true
```

### 3. Yahoo

```env
EMAIL_HOST=yahoo
EMAIL_USERNAME=your_email@yahoo.com
EMAIL_PASSWORD=your_app_password
EMAIL_PORT=993
EMAIL_USE_SSL=true
```

**Note**: For Yahoo, you need to:
1. Enable 2-factor authentication
2. Generate an "App Password"
3. Use the app password in `EMAIL_PASSWORD`

### 4. Custom Domain (like bchainre.com)

#### Option A: Auto-detection
```env
EMAIL_HOST=custom
EMAIL_USERNAME=ravi@bchainre.com
EMAIL_PASSWORD=your_password
EMAIL_PORT=993
EMAIL_USE_SSL=true
```

#### Option B: Custom server
```env
EMAIL_HOST=custom
EMAIL_SERVER=mail.bchainre.com
EMAIL_USERNAME=ravi@bchainre.com
EMAIL_PASSWORD=your_password
EMAIL_PORT=993
EMAIL_USE_SSL=true
```

#### Option C: Different port
```env
EMAIL_HOST=custom
EMAIL_SERVER=mail.bchainre.com
EMAIL_USERNAME=ravi@bchainre.com
EMAIL_PASSWORD=your_password
EMAIL_PORT=587
EMAIL_USE_SSL=false
```

## Supported Ports

- **143**: IMAP (non-SSL)
- **993**: IMAP (SSL) - **Recommended**
- **587**: SMTP (TLS)
- **465**: SMTP (SSL)

## Configuration Examples

### For ravi@bchainre.com (Cash App emails)

```env
# Email Configuration
EMAIL_HOST=custom
EMAIL_SERVER=mail.bchainre.com
EMAIL_PORT=993
EMAIL_USERNAME=ravi@bchainre.com
EMAIL_PASSWORD=your_password
EMAIL_USE_SSL=true

# Database Configuration
DATABASE_URL=sqlite:///transactions.db

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
```

### For Gmail (testing)

```env
# Email Configuration
EMAIL_HOST=gmail
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_PORT=993
EMAIL_USE_SSL=true

# Database Configuration
DATABASE_URL=sqlite:///transactions.db

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
```

## Testing Your Configuration

1. **Start the server**:
   ```bash
   python -m uvicorn src.email_parser.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Test connection**:
   ```bash
   curl http://localhost:8000/api/v1/status
   ```

3. **Test email sync**:
   ```bash
   # Search by sender (Cash App)
   curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com?limit=5"
   
   # Search by content
   curl -X POST "http://localhost:8000/api/v1/sync/content/cash@square.com?limit=5"
   
   # Search with date range
   curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com/date-range?start_date=2024-01-01"
   ```

## Troubleshooting

### Connection Issues

1. **Check server address**: Verify `EMAIL_SERVER` is correct
2. **Check port**: Most providers use 993 for SSL, 143 for non-SSL
3. **Check credentials**: Ensure username/password are correct
4. **Check SSL**: Some providers require SSL, others don't

### Gmail Issues

1. **"Invalid credentials"**: Use App Password, not regular password
2. **"Access denied"**: Enable "Less secure app access" or use App Password

### Custom Domain Issues

1. **"Connection refused"**: Check if the mail server is running
2. **"Authentication failed"**: Verify username/password format
3. **"SSL error"**: Try different ports (993, 143, 587)

## Security Notes

- **Never commit `.env` files** to version control
- **Use App Passwords** for Gmail/Yahoo when possible
- **Use strong passwords** for email accounts
- **Consider using environment variables** in production
