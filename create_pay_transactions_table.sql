-- Create pay_transactions table in staging schema
-- Run this in your Supabase SQL Editor

-- Create staging schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS staging;

-- Grant permissions to service_role for staging schema
GRANT USAGE ON SCHEMA staging TO service_role, anon, authenticated;
GRANT ALL ON SCHEMA staging TO service_role;

-- Create the pay_transactions table in staging schema
CREATE TABLE IF NOT EXISTS staging.pay_transactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    amount_paid DECIMAL(10,2) NOT NULL,
    paid_by TEXT,
    paid_to TEXT,
    payment_status TEXT DEFAULT 'completed',
    transaction_number TEXT,
    transaction_date TIMESTAMP WITH TIME ZONE,
    payment_provider TEXT DEFAULT 'cashapp',
    source TEXT DEFAULT 'email-reader-api',
    raw_data JSONB,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Grant permissions to service_role
GRANT ALL ON staging.pay_transactions TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON staging.pay_transactions TO authenticated, anon;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_pay_transactions_user_id ON staging.pay_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_pay_transactions_transaction_date ON staging.pay_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_pay_transactions_transaction_number ON staging.pay_transactions(transaction_number);

-- Add RLS (Row Level Security) if needed
ALTER TABLE staging.pay_transactions ENABLE ROW LEVEL SECURITY;

-- Create policy for service_role (allows full access)
DROP POLICY IF EXISTS "Service role can do everything" ON staging.pay_transactions;
CREATE POLICY "Service role can do everything" ON staging.pay_transactions
    FOR ALL TO service_role USING (true) WITH CHECK (true);
