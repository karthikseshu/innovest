-- ============================================================================
-- EXPOSE STAGING SCHEMA TO SUPABASE API (PostgREST)
-- ============================================================================
-- This script configures the staging schema to be accessible via Supabase API
-- Run this in your Supabase SQL Editor
-- ============================================================================

-- Step 1: Create staging schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS staging;

-- Step 2: Grant schema-level permissions to all relevant roles
-- (Same as api schema configuration)
GRANT USAGE ON SCHEMA staging TO anon, authenticated, service_role;
GRANT ALL ON SCHEMA staging TO service_role;
GRANT USAGE ON SCHEMA staging TO postgres;

-- Step 3: Grant permissions on all existing tables in staging schema
GRANT ALL ON ALL TABLES IN SCHEMA staging TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA staging TO authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA staging TO anon;

-- Step 4: Grant permissions on all sequences (for auto-increment/serial columns)
GRANT ALL ON ALL SEQUENCES IN SCHEMA staging TO service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA staging TO authenticated;

-- Step 5: Grant permissions on all functions/routines
GRANT ALL ON ALL ROUTINES IN SCHEMA staging TO service_role;
GRANT EXECUTE ON ALL ROUTINES IN SCHEMA staging TO authenticated;

-- Step 6: Set default privileges for future objects in staging schema
-- This ensures new tables/sequences/functions automatically get proper permissions
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging 
    GRANT ALL ON TABLES TO service_role;
    
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;
    
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging 
    GRANT SELECT ON TABLES TO anon;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging 
    GRANT ALL ON SEQUENCES TO service_role;
    
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging 
    GRANT USAGE, SELECT ON SEQUENCES TO authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging 
    GRANT ALL ON ROUTINES TO service_role;
    
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA staging 
    GRANT EXECUTE ON ROUTINES TO authenticated;

-- ============================================================================
-- VERIFICATION QUERIES (Run these to verify configuration)
-- ============================================================================

-- Check schema permissions
SELECT 
    nspname as schema_name,
    nspacl as schema_acl
FROM pg_namespace 
WHERE nspname IN ('api', 'staging')
ORDER BY nspname;

-- Check if roles have USAGE on schemas
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

-- ============================================================================
-- IMPORTANT: CONFIGURE POSTGREST TO EXPOSE STAGING SCHEMA
-- ============================================================================
-- After running this SQL, you need to configure PostgREST to expose the staging schema.
-- 
-- There are TWO ways to do this:
--
-- METHOD 1: Via Supabase Dashboard (RECOMMENDED for Supabase Cloud)
-- -----------------------------------------------------------------------
-- 1. Go to your Supabase project dashboard
-- 2. Navigate to Settings > API > "API Settings"
-- 3. Look for "Exposed schemas" or "Extra search path" setting
-- 4. Add 'staging' to the list of exposed schemas
-- 5. The setting should look like: public,api,staging
-- 6. Save and restart the API
--
-- METHOD 2: Via SQL (for self-hosted Supabase only)
-- -----------------------------------------------------------------------
-- This method only works if you have database-level configuration access
-- (typically only available for self-hosted Supabase instances)

-- Check current PostgREST schema configuration
SELECT name, setting, context 
FROM pg_settings 
WHERE name LIKE '%search_path%' OR name LIKE '%db_schema%';

-- Attempt to set db-schemas (this might not work on Supabase Cloud)
-- ALTER DATABASE postgres SET "app.settings.db_schema" = 'public,api,staging';

-- If the above doesn't work, try setting the search_path
-- ALTER DATABASE postgres SET search_path TO public, api, staging;

-- Notify PostgREST to reload configuration (if supported)
-- NOTIFY pgrst, 'reload config';

-- ============================================================================
-- TROUBLESHOOTING
-- ============================================================================
-- If you still get "The schema must be one of the following: api" error after
-- running this SQL, it means PostgREST is not configured to expose the staging
-- schema. This is a PostgREST configuration issue, not a PostgreSQL permission issue.
--
-- For Supabase Cloud projects:
-- - You MUST use the dashboard to add staging to exposed schemas
-- - Or contact Supabase support to enable custom schema exposure
-- - Or use the 'api' schema for your tables (which is already exposed)
--
-- For self-hosted Supabase:
-- - Update your PostgREST configuration file
-- - Set db-schemas = "public, api, staging"
-- - Restart PostgREST service
-- ============================================================================

