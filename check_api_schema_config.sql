-- ============================================================================
-- CHECK API SCHEMA CONFIGURATION
-- ============================================================================
-- Run these queries to see how the 'api' schema is configured
-- Then we can replicate the same for 'staging' schema
-- ============================================================================

-- 1. Check schema ACLs (Access Control Lists)
SELECT 
    nspname as schema_name,
    nspacl as schema_acl,
    pg_catalog.pg_get_userbyid(nspowner) as owner
FROM pg_namespace 
WHERE nspname IN ('public', 'api', 'staging')
ORDER BY nspname;

-- 2. Check role permissions on schemas
SELECT 
    n.nspname as schema_name,
    r.rolname as role_name,
    has_schema_privilege(r.rolname, n.nspname, 'USAGE') as has_usage,
    has_schema_privilege(r.rolname, n.nspname, 'CREATE') as has_create
FROM pg_namespace n
CROSS JOIN pg_roles r
WHERE n.nspname IN ('public', 'api', 'staging')
    AND r.rolname IN ('anon', 'authenticated', 'service_role', 'postgres', 'authenticator')
ORDER BY n.nspname, r.rolname;

-- 3. Check table permissions in api schema
SELECT 
    schemaname,
    tablename,
    tableowner,
    hasindexes,
    rowsecurity as has_rls
FROM pg_tables
WHERE schemaname IN ('api', 'staging')
ORDER BY schemaname, tablename;

-- 4. Check default privileges
SELECT 
    pg_catalog.pg_get_userbyid(defaclrole) as grantor,
    defaclnamespace::regnamespace as schema,
    defaclobjtype as object_type,
    defaclacl as default_acl
FROM pg_default_acl
WHERE defaclnamespace IN (
    SELECT oid FROM pg_namespace WHERE nspname IN ('api', 'staging')
);

-- 5. Check PostgREST configuration (if accessible)
SELECT name, setting, context, source
FROM pg_settings 
WHERE name LIKE '%search_path%' 
   OR name LIKE '%pgrst%'
   OR name LIKE '%db_schema%'
   OR name LIKE '%app.settings%';

-- 6. Check if staging schema exists
SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name IN ('public', 'api', 'staging');

-- 7. Check RLS policies on tables in api schema
SELECT 
    schemaname,
    tablename,
    policyname,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'api'
ORDER BY tablename, policyname;

-- 8. Check grants on specific tables
SELECT 
    grantee,
    table_schema,
    table_name,
    privilege_type
FROM information_schema.table_privileges
WHERE table_schema IN ('api', 'staging')
ORDER BY table_schema, table_name, grantee;

-- ============================================================================
-- NEXT STEPS AFTER RUNNING THESE QUERIES:
-- ============================================================================
-- 1. Compare the permissions between 'api' and 'staging' schemas
-- 2. If 'api' has permissions that 'staging' doesn't, grant them
-- 3. Most importantly, check if there's a PostgREST configuration that 
--    lists exposed schemas (likely not accessible via SQL in Supabase Cloud)
-- 4. You may need to use Supabase Dashboard to expose the staging schema
-- ============================================================================

