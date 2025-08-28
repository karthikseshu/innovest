#!/usr/bin/env python3
"""
Database setup script for Email Transaction Parser.
"""
import sys
import os
import logging

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import after fixing the path
from email_parser.models.database import init_db, check_db_connection
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Main setup function."""
    print("🚀 Setting up Email Transaction Parser Database...")
    print(f"📧 Email Host: {settings.email_host}")
    print(f"💾 Database URL: {settings.database_url}")
    print()
    
    try:
        # Test database connection
        print("🔍 Testing database connection...")
        if check_db_connection():
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            print("Please check your database configuration in .env file")
            return False
        
        # Initialize database tables
        print("🏗️  Creating database tables...")
        init_db()
        print("✅ Database tables created successfully")
        
        # Verify tables were created
        print("🔍 Verifying database tables...")
        try:
            import sqlite3
            conn = sqlite3.connect('transactions.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            
            if tables:
                print(f"✅ Tables created: {[table[0] for table in tables]}")
            else:
                print("❌ No tables found in database")
                return False
                
        except Exception as e:
            print(f"❌ Error verifying tables: {e}")
            return False
        
        print()
        print("🎉 Database setup completed successfully!")
        print()
        print("Next steps:")
        print("1. Configure your email settings in .env file")
        print("2. Run the application: uvicorn src.email_parser.api.main:app --reload")
        print("3. Visit http://localhost:8000/docs for API documentation")
        
        return True
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        print(f"❌ Setup failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
