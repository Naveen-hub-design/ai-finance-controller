-- Extensions required by the AI Finance Controller foundation.
-- Applied automatically on first container initialization via
-- /docker-entrypoint-initdb.d/.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
