#!/usr/bin/env bash
# Prepare the local environment file from the committed example.
# Safe to re-run: refuses to overwrite an existing .env.

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
    echo ".env already exists — nothing to do."
    exit 0
fi

cp .env.example .env
echo "Created .env from .env.example."
echo "IMPORTANT: review the placeholder values before deploying anywhere."
