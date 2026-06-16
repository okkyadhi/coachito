-- Core extensions for Coachito
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The codebase uses a hand-written SQL ``uuid_generate_v7()`` function
-- defined in alembic migration 0001 (built on uuid-ossp).  We do NOT try
-- to load the pg_uuidv7 extension here — it isn't in the official
-- postgres:16-alpine image and the resulting CREATE EXTENSION error
-- aborts the init pipeline (psql runs with ON_ERROR_STOP), which
-- would prevent 02-app-user.sql from creating the coachito_api role.
