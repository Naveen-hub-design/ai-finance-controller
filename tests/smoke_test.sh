#!/usr/bin/env bash
# Cross-service smoke test for the M01 foundation.
# Requires the stack to be running: docker compose up --build

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"
failures=0

check() {
    local name="$1" url="$2" expected="$3"
    if curl -fsS "$url" | grep -q "$expected"; then
        echo "PASS: $name"
    else
        echo "FAIL: $name (expected '$expected' at $url)"
        failures=$((failures + 1))
    fi
}

check "API health payload"   "$BASE_URL/api/health" '"status": "healthy"'
check "API service name"     "$BASE_URL/api/health" 'finance-controller-api'
check "Frontend page"        "$BASE_URL/"           'AI Finance Controller'

if [[ "$failures" -ne 0 ]]; then
    echo "Smoke test FAILED: $failures check(s) failed."
    exit 1
fi

echo "Smoke test PASSED."
