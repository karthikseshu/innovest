-- ============================================
-- Add sender_emails column to api.email_integrations
-- ============================================
-- This column stores which payment provider email addresses to search for
-- Example: ['cash@square.com', 'venmo@venmo.com', 'karthik_seshu@yahoo.com']
--
-- Run this in your Supabase SQL Editor

-- Add sender_emails column as TEXT array
ALTER TABLE api.email_integrations 
ADD COLUMN IF NOT EXISTS sender_emails TEXT[] DEFAULT ARRAY['cash@square.com'];

-- Add comment to explain the column
COMMENT ON COLUMN api.email_integrations.sender_emails IS 
'Array of email addresses to search for payment transactions. These are the sender emails (e.g., cash@square.com, venmo@venmo.com) that the system will look for in the user''s Gmail account.';

-- ============================================
-- Update existing records (optional)
-- ============================================

-- Example 1: Set Cash App as default for all existing OAuth integrations
-- UPDATE api.email_integrations 
-- SET sender_emails = ARRAY['cash@square.com']
-- WHERE integration_type = 'oauth' 
-- AND (sender_emails IS NULL OR sender_emails = '{}');

-- Example 2: Set multiple payment providers for a specific user
-- UPDATE api.email_integrations 
-- SET sender_emails = ARRAY['cash@square.com', 'venmo@venmo.com', 'service@paypal.com']
-- WHERE user_id = 'YOUR_USER_ID';

-- Example 3: Set a specific email address (e.g., personal email forwarding payments)
-- UPDATE api.email_integrations 
-- SET sender_emails = ARRAY['karthik_seshu@yahoo.com']
-- WHERE email_username = 'aiinnovest@gmail.com';

-- ============================================
-- Verify the changes
-- ============================================

-- Check all integrations and their sender_emails
SELECT 
    id,
    user_id,
    email_username,
    integration_type,
    sender_emails,
    is_active
FROM api.email_integrations
ORDER BY created_at DESC;

-- ============================================
-- Common Sender Emails Reference
-- ============================================
-- Use these as examples for your sender_emails configuration:
--
-- Cash App:    'cash@square.com'
-- Venmo:       'venmo@venmo.com'
-- PayPal:      'service@paypal.com'
-- Zelle:       'noreply@zellepay.com'
-- Apple Cash:  'no_reply@email.apple.com'
-- Google Pay:  'googlepay-noreply@google.com'
--
-- Personal emails can also be added if users forward payment receipts
-- ============================================

