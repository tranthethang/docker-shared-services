-- Ensure GoTrue can CREATE OR REPLACE auth helper functions on first boot.
-- The image migration 20211124212715_update-auth-owner.sql uses
-- "ALTER FUNCTION auth.uid" without "()" and swallows errors, so on PG 17
-- ownership stays with postgres and supabase-auth crashes with:
--   ERROR: must be owner of function uid (SQLSTATE 42501)
ALTER FUNCTION auth.uid() OWNER TO supabase_auth_admin;
ALTER FUNCTION auth.role() OWNER TO supabase_auth_admin;
ALTER FUNCTION auth.email() OWNER TO supabase_auth_admin;
