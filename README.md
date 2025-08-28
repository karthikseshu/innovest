# Email Transaction Parser

A pluggable utility API for extracting transaction information from emails and storing them in a database. Originally designed for Cash App emails but easily extensible for other email providers.

## Features

- 🔌 **Pluggable Architecture**: Easy to extend for different email providers
- 📧 **Email Processing**: IMAP-based email fetching and parsing
- 💾 **Database Storage**: SQLAlchemy ORM with support for multiple databases
- 🚀 **FastAPI Backend**: RESTful API with automatic documentation
- ⚙️ **Configurable**: Environment-based configuration for email and database settings
- 🔄 **Transaction Deduplication**: Prevents duplicate transaction processing

## Project Structure

```
email-reader/
├── src/
│   └── email_parser/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── email_client.py
│       │   ├── parser_factory.py
│       │   └── transaction_processor.py
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── base_parser.py
│       │   └── cashapp_parser.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── database.py
│       │   └── transaction.py
│       └── api/
│           ├── __init__.py
│           ├── main.py
│           └── routes.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── tests/
│   ├── __init__.py
│   ├── test_parsers.py
│   └── test_api.py
├── scripts/
│   └── setup_db.py
├── .env.example
├── .gitignore
├── requirements.txt
├── setup.py
└── README.md
```

## Quick Start

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd email-reader
```

### 2. Set up environment
```bash
cp .env.example .env
# Edit .env with your email and database credentials
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up database
```bash
python scripts/setup_db.py
```

### 5. Run the application
```bash
uvicorn src.email_parser.api.main:app --reload
```

## Configuration

Create a `.env` file with the following variables:

```env
# Email Configuration
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USER=your-email@gmail.com
EMAIL_PASS=your-app-password

# Database Configuration
DB_URL=sqlite:///./transactions.db
# or for PostgreSQL: postgresql://user:password@localhost/dbname

# Application Configuration
LOG_LEVEL=INFO
```

## API Endpoints

### Health & Status
- `GET /api/v1/health` - Health check
- `GET /api/v1/status` - Service status

### Database
- `POST /api/v1/init-db` - Initialize database tables

### Transactions
- `GET /api/v1/transactions` - Get all transactions (with pagination)
- `GET /api/v1/transactions/{transaction_id}` - Get specific transaction

### Email Syncing

#### By Sender
- `POST /api/v1/sync/sender/{sender_email}` - Sync emails from specific sender
  - Query params: `limit` (optional, 0 = all emails)
- `POST /api/v1/sync/sender/{sender_email}/date-range` - Sync emails from sender in date range
  - Query params: `start_date` (required, YYYY-MM-DD), `end_date` (optional, YYYY-MM-DD)

#### By Content
- `POST /api/v1/sync/content/{search_text}` - Sync emails containing specific text
  - Query params: `limit` (optional, 0 = all emails)
- `POST /api/v1/sync/content/{search_text}/date-range` - Sync emails with content in date range
  - Query params: `start_date` (required, YYYY-MM-DD), `end_date` (optional, YYYY-MM-DD)

#### By Subject
- `POST /api/v1/sync/subject/{search_text}` - Sync emails by subject line
  - Query params: `limit` (optional, 0 = all emails)

### Examples

```bash
# Sync last 10 emails from Cash App
curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com?limit=10"

# Sync all emails from Cash App (no limit)
curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com"

# Sync Cash App emails from specific date range
curl -X POST "http://localhost:8000/api/v1/sync/sender/cash@square.com/date-range?start_date=2024-01-01&end_date=2024-12-31"

# Sync emails containing "cash@square.com" in content
curl -X POST "http://localhost:8000/api/v1/sync/content/cash@square.com?limit=50"

# Sync emails with "cash@square.com" content in date range
curl -X POST "http://localhost:8000/api/v1/sync/content/cash@square.com/date-range?start_date=2024-01-01"
```

## Extending for New Email Providers

1. Create a new parser class inheriting from `BaseParser`
2. Implement the required parsing methods
3. Register the parser in the `ParserFactory`
4. Update configuration to use the new parser

Example:
```python
from src.email_parser.parsers.base_parser import BaseParser

class PayPalParser(BaseParser):
    def parse_transaction(self, email_body: str) -> dict:
        # Implement PayPal-specific parsing logic
        pass
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black src/ tests/
```

### Type Checking
```bash
mypy src/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details
