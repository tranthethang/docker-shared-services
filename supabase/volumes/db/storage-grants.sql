-- Storage API (supabase_storage_admin) SET ROLEs to JWT roles when listing
-- buckets / enforcing RLS. Without these memberships, Studio returns 500 on
-- /api/platform/storage/.../buckets with:
--   permission denied to set role "service_role"
--
-- Official postgres images sometimes also grant authenticator; keep both so
-- storage-api can SET ROLE service_role / anon / authenticated directly.
GRANT anon, authenticated, service_role TO supabase_storage_admin;
GRANT authenticator TO supabase_storage_admin;
