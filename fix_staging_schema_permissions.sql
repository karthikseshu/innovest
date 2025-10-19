-- ============================================================================
-- FIX STAGING SCHEMA PERMISSIONS TO MATCH API SCHEMA
-- ============================================================================
-- Based on the analysis, staging schema is missing 'anon' role USAGE permission
-- This SQL will make staging schema permissions identical to api schema
-- ============================================================================

-- Step 1: Grant USAGE to anon role (THIS IS THE MISSING PERMISSION!)
GRANT USAGE ON SCHEMA staging TO anon;

-- Step 2: Grant table-level permissions to anon for pay_transactions
GRANT SELECT, INSERT, UPDATE, DELETE ON staging.pay_transactions TO anon;

-- Step 3: Grant table-level permissions to authenticated for pay_transactions
GRANT SELECT, INSERT, UPDATE, DELETE ON staging.pay_transactions TO authenticated;

-- Step 4: Grant ALL permissions to service_role for pay_transactions
GRANT ALL ON staging.pay_transactions TO service_role;

-- Step 5: Grant sequence permissions (if any sequences exist)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA staging TO anon;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA staging TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA staging TO service_role;

-- Step 6: Set default privileges for future objects
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging 
    GRANT ALL ON TABLES TO service_role;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging 
    GRANT USAGE, SELECT ON SEQUENCES TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging 
    GRANT USAGE, SELECT ON SEQUENCES TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging 
    GRANT ALL ON SEQUENCES TO service_role;

-- ============================================================================
-- VERIFY THE FIX
-- ============================================================================

-- Check schema permissions (should now match api schema)
SELECT 
    n.nspname as schema_name,
    r.rolname as role_name,
    has_schema_privilege(r.rolname, n.nspname, 'USAGE') as has_usage,
    has_schema_privilege(r.rolname, n.nspname, 'CREATE') as has_create
FROM pg_namespace n
CROSS JOIN pg_roles r
WHERE n.nspname IN ('api', 'staging')
    AND r.rolname IN ('anon', 'authenticated', 'service_role', 'postgres')
ORDER BY n.nspname, r.rolname;

-- Check table grants (should show anon now has permissions)
SELECT 
    grantee,
    table_schema,
    table_name,
    privilege_type
FROM information_schema.table_privileges
WHERE table_schema = 'staging'
    AND table_name = 'pay_transactions'
ORDER BY grantee, privilege_type;

-- Check ACLs
SELECT 
    nspname as schema_name,
    nspacl as schema_acl
FROM pg_namespace 
WHERE nspname IN ('api', 'staging')
ORDER BY nspname;

-- ============================================================================
-- IMPORTANT: CONFIGURE POSTGREST
-- ============================================================================
-- After running this SQL, you STILL need to expose the staging schema in PostgREST.
-- 
-- Go to your Supabase Dashboard:
-- 1. Settings → API → API Settings
-- 2. Find "Exposed schemas" or contact Supabase support
-- 3. Add 'staging' to the list: public,api,staging
-- 
-- WITHOUT this PostgREST configuration, you will still get the error:
-- "The schema must be one of the following: api"
-- 
-- This is because PostgREST (Supabase's API layer) needs to be told which
-- schemas to expose via the REST API, even if PostgreSQL permissions are correct.
-- ============================================================================

