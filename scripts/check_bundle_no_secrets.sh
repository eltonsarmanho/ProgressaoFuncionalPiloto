#!/usr/bin/env bash
# VER-07 / EXT-06: the production frontend bundle must not carry the MariTalk key or its name.
# Usage: scripts/check_bundle_no_secrets.sh [bundle-dir]   (default: frontend/dist, after `npm run build`)
# Exit 0 = clean; 1 = a forbidden string was found; 2 = the directory does not exist.
set -euo pipefail

dir="${1:-$(dirname "$0")/../frontend/dist}"
if [ ! -d "$dir" ]; then
  echo "bundle directory not found: $dir (run 'npm run build' in frontend/ first)" >&2
  exit 2
fi

# MARITALK in any case; an Authorization Bearer token; key-like tokens (sk-/mk-/key-/api- + 20 chars).
patterns=(
  -e 'maritalk'
  -e 'Bearer[[:space:]]+[A-Za-z0-9._~+/=-]{20,}'
  -e '(^|[^A-Za-z0-9])(sk|mk|key|api)[-_][A-Za-z0-9]{20,}'
)

if grep -rIlEi "${patterns[@]}" "$dir" >&2; then
  echo "forbidden string found in the bundle (files listed above)" >&2
  exit 1
fi
echo "bundle is clean: $dir"
