-- Realtime schemas for self-hosted stack.
-- Upstream: docker/volumes/db/realtime.sql (_realtime only).
-- Also ensure `realtime` (WALRUS / postgres_changes) exists — normally created
-- by the supabase/postgres image migration, but may be missing on older volumes.
\set pguser `echo "$POSTGRES_USER"`

create schema if not exists _realtime;
alter schema _realtime owner to :pguser;

create schema if not exists realtime;
alter schema realtime owner to supabase_admin;
grant usage on schema realtime to postgres, anon, authenticated, service_role;
grant all on all tables in schema realtime to postgres, anon, authenticated, service_role;
grant all on all sequences in schema realtime to postgres, anon, authenticated, service_role;
grant all on all routines in schema realtime to postgres, anon, authenticated, service_role;
alter default privileges for role supabase_admin in schema realtime
  grant all on tables to postgres, anon, authenticated, service_role;
alter default privileges for role supabase_admin in schema realtime
  grant all on sequences to postgres, anon, authenticated, service_role;
alter default privileges for role supabase_admin in schema realtime
  grant all on routines to postgres, anon, authenticated, service_role;
