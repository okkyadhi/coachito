-- Non-superuser application role used by the API at runtime.
-- Migrations still run as the superuser (coachito); the API connects as coachito_api.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'coachito_api') THEN
        CREATE ROLE coachito_api LOGIN PASSWORD 'coachito_api';
    END IF;
END;
$$;

GRANT CONNECT ON DATABASE coachito TO coachito_api;
GRANT USAGE ON SCHEMA public TO coachito_api;

-- Grant DML on all existing tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO coachito_api;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO coachito_api;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO coachito_api;

-- Ensure future tables/sequences are accessible too
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO coachito_api;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO coachito_api;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO coachito_api;
