FROM pgvector/pgvector:pg16

# Extensions are applied first so pgcrypto/gen_random_uuid() is available to
# the core schema that follows.
COPY init/*.sql /docker-entrypoint-initdb.d/

# The schema files are staged into order-safe names so that, inside
# /docker-entrypoint-initdb.d/ (which runs in alphabetical order), they execute
# as: 001_extensions -> 010_core_schema -> 020_m4_audit -> 030_password_hash
# -> 040_controller_tasks -> 050_roles_businesses -> 060_statement_lines ->
# 070_audit_reconciliation -> 080_statement_line_review.
# The source schema files themselves are never renamed or duplicated.
# 030_password_hash is an idempotent forward migration that brings a
# pre-authentication volume up to date (ADD COLUMN IF NOT EXISTS).
# 040_controller_tasks is required for the async AI controller ownership flow
# and is idempotent (CREATE TABLE IF NOT EXISTS).
# 050_roles_businesses adds users.role plus the businesses/business_members
# tables for the F9.x.1 role + multi-user architecture. It is additive and
# idempotent, so it also runs safely against an already-populated volume.
# 060_statement_lines adds the external-source table for the multi-source
# reconciliation agent. It is additive and idempotent (CREATE TABLE IF NOT
# EXISTS).
# 070_audit_reconciliation widens the audit_records kind CHECK to include
# 'reconciliation' so the reconciliate loop can persist its immutable audit.
# 080_statement_line_review adds per-line exception category + human-review
# status columns to statement_lines (idempotent ADD COLUMN IF NOT EXISTS).
# 090_audit_business_id and 100_controller_task_business_id add the
# business-scoping columns for business-scoped audit + async task ownership
# (idempotent ADD COLUMN IF NOT EXISTS).
#
# NOTE: /docker-entrypoint-initdb.d/ only executes against an EMPTY data
# directory. Existing persistent volumes receive these same (idempotent) schema
# files from the docker-compose `migrate` one-shot service on every `docker
# compose up`.
COPY schema/ /tmp/schema/
RUN cp /tmp/schema/001_core_financial_model.sql /docker-entrypoint-initdb.d/010_core_schema.sql \
 && cp /tmp/schema/002_m4_audit.sql /docker-entrypoint-initdb.d/020_m4_audit.sql \
 && cp /tmp/schema/003_password_hash.sql /docker-entrypoint-initdb.d/030_password_hash.sql \
 && cp /tmp/schema/003_controller_tasks.sql /docker-entrypoint-initdb.d/040_controller_tasks.sql \
 && cp /tmp/schema/004_roles_businesses.sql /docker-entrypoint-initdb.d/050_roles_businesses.sql \
 && cp /tmp/schema/005_statement_lines.sql /docker-entrypoint-initdb.d/060_statement_lines.sql \
 && cp /tmp/schema/006_audit_kind_reconciliation.sql /docker-entrypoint-initdb.d/070_audit_reconciliation.sql \
 && cp /tmp/schema/007_statement_line_review.sql /docker-entrypoint-initdb.d/080_statement_line_review.sql \
 && cp /tmp/schema/008_audit_business_id.sql /docker-entrypoint-initdb.d/090_audit_business_id.sql \
 && cp /tmp/schema/009_controller_task_business_id.sql /docker-entrypoint-initdb.d/100_controller_task_business_id.sql \
 && rm -rf /tmp/schema
