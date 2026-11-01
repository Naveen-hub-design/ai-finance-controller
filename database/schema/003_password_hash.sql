-- AI Finance Controller
-- Forward migration: ensure users.password_hash exists.
--
-- The users.password_hash column (added in M7 security hardening) was not
-- present in database volumes initialised before that milestone, because the
-- Docker entrypoint init scripts (/docker-entrypoint-initdb.d/) only run once
-- against an empty volume. This idempotent migration brings an existing
-- volume up to date without dropping or recreating any data.
--
-- Safe to run multiple times: ADD COLUMN IF NOT EXISTS is a no-op once the
-- column exists.

ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
