FROM pgvector/pgvector:pg16

# Extensions are applied first so pgcrypto/gen_random_uuid() is available to
# the core schema that follows.
COPY init/*.sql /docker-entrypoint-initdb.d/

# The schema files are staged into order-safe names so that, inside
# /docker-entrypoint-initdb.d/ (which runs in alphabetical order), they execute
# as: 001_extensions -> 010_core_schema -> 020_m4_audit.
# The source schema files themselves are never renamed or duplicated.
COPY schema/ /tmp/schema/
RUN cp /tmp/schema/001_core_financial_model.sql /docker-entrypoint-initdb.d/010_core_schema.sql \
 && cp /tmp/schema/002_m4_audit.sql /docker-entrypoint-initdb.d/020_m4_audit.sql \
 && rm -rf /tmp/schema
