#!/usr/bin/env python3
"""
Simple database creation script.
"""
import sqlite3
import os

def create_database():
    """Create the database and tables directly."""
    
    # Remove existing database file if it exists
    if os.path.exists('transactions.db'):
        os.remove('transactions.db')
        print("🗑️  Removed existing database file")
    
    # Create new database
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    
    # Create transactions table with all required columns
    cursor.execute('''
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE NOT NULL,
            sender TEXT NOT NULL,
            recipient TEXT,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            transaction_type TEXT DEFAULT 'transfer',
            status TEXT DEFAULT 'completed',
            description TEXT,
            email_subject TEXT,
            email_date TEXT,
            source_provider TEXT NOT NULL,
            raw_email_data TEXT,
            deposited_to TEXT,
            cashapp_transaction_number TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX idx_transaction_id ON transactions(transaction_id)')
    cursor.execute('CREATE INDEX idx_sender ON transactions(sender)')
    cursor.execute('CREATE INDEX idx_source_provider ON transactions(source_provider)')
    cursor.execute('CREATE INDEX idx_provider_date ON transactions(source_provider, created_at)')
    cursor.execute('CREATE INDEX idx_amount_date ON transactions(amount, created_at)')
    
    # Commit and close
    conn.commit()
    conn.close()
    
    print("✅ Database created successfully!")
    print("✅ Transactions table created with all required fields")
    print("✅ Indexes created for better performance")
    
    # Verify the table was created
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()
    
    print(f"📊 Tables in database: {[table[0] for table in tables]}")
    
    # Check table structure
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(transactions);")
    columns = cursor.fetchall()
    conn.close()
    
    print(f"📋 Table has {len(columns)} columns:")
    for col in columns:
        print(f"   - {col[1]} ({col[2]})")

if __name__ == "__main__":
    create_database()
