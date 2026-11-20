#!/usr/bin/env bash
# End-to-end smoke test of the compose stack (INFRA-01, INFRA-04, INFRA-05, DOC-03).
# Uses its own generated env file and project name; never reads the project .env.
# Always tears down with `down -v` on exit.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="pd_smoke"
HTTP_PORT="${SMOKE_HTTP_PORT:-8088}"
BASE="http://127.0.0.1:${HTTP_PORT}"
ADMIN_EMAIL="admin@smoke.local"
ADMIN_PASSWORD="smoke-admin-password"

WORK="$(mktemp -d)"
ENV_FILE="$WORK/smoke.env"
JAR="$WORK/cookies.txt"

cat > "$ENV_FILE" <<ENV
POSTGRES_USER=smoke
POSTGRES_PASSWORD=smoke-db-password
POSTGRES_DB=smoke
DATABASE_URL=postgresql+psycopg://smoke:smoke-db-password@postgres:5432/smoke
ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
COOKIE_SECURE=false
HTTP_PORT=${HTTP_PORT}
MARITALK_API_KEY=
MARITALK_API_BASE=
MARITALK_MODEL=
ENV

compose() {
  docker compose --progress quiet --env-file "$ENV_FILE" -p "$PROJECT" -f "$ROOT/docker-compose.yml" "$@"
}

cleanup() {
  compose down -v --remove-orphans --rmi local >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  compose logs --tail 30 >&2 2>/dev/null || true
  exit 1
}

json_field() { python3 -c "import json,sys; print(json.load(sys.stdin)$1)"; }

# Health must be 200 within 120 s of `up` (INFRA-01); $1 = SECONDS when `up` started.
wait_health() {
  local start=$1 body
  while (( SECONDS - start <= 120 )); do
    if body="$(curl -fsS "$BASE/api/health" 2>/dev/null)"; then
      [ "$body" = '{"status":"ok","database":"ok"}' ] || fail "unexpected health body: $body"
      echo "    health 200 via nginx $((SECONDS - start)) s after up"
      return 0
    fi
    sleep 2
  done
  fail "health did not return 200 within 120 s"
}

login() {
  rm -f "$JAR"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' -c "$JAR" -H 'Content-Type: application/json' \
    -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" "$BASE/api/auth/login")"
  [ "$code" = "200" ] || fail "admin login returned $code"
  grep -q $'\tsession\t' "$JAR" || fail "login did not set the session cookie"
  local me
  me="$(curl -fsS -b "$JAR" "$BASE/api/auth/me")" || fail "GET /api/auth/me did not return 200"
  CSRF="$(echo "$me" | json_field "['csrf_token']")"
  [ "$(echo "$me" | json_field "['role']")" = "ADMIN" ] || fail "/api/auth/me is not the ADMIN"
  echo "    admin login ok, session cookie set, /api/auth/me 200"
}

echo "==> .env.example lists every variable used by docker-compose.yml"
for var in $(grep -oE '\$\{[A-Z_]+' "$ROOT/docker-compose.yml" | cut -c3- | sort -u); do
  grep -qE "^${var}=" "$ROOT/.env.example" || fail ".env.example is missing $var"
done

if curl -s -o /dev/null "$BASE" 2>/dev/null; then fail "port $HTTP_PORT is already in use"; fi

echo "==> build images"
compose build -q
echo "==> up"
up_start=$SECONDS
compose up -d
wait_health "$up_start"

published="$(compose ps --format json | python3 -c "
import json, sys
text = sys.stdin.read().strip()
rows = json.loads(text) if text.startswith('[') else [json.loads(l) for l in text.splitlines() if l]
print(' '.join(sorted({r['Service'] for r in rows for p in (r.get('Publishers') or []) if p.get('PublishedPort')})))")"
[ "$published" = "nginx" ] || fail "only nginx may publish ports (got: $published)"
echo "    only nginx publishes a host port"

echo "==> frontend"
html="$(curl -fsS "$BASE/")" || fail "GET / failed"
echo "$html" | grep -q '<div id="root"></div>' || fail "GET / did not return the SPA HTML"
deep="$(curl -fsS "$BASE/processos/novo")" || fail "SPA fallback failed"
[ "$deep" = "$html" ] || fail "deep link did not return the SPA HTML"
echo "    / and deep links return the SPA HTML"

echo "==> login and create data"
login
unit_id="$(curl -fsS -b "$JAR" "$BASE/api/units" | python3 -c "import json,sys; print(next(u['id'] for u in json.load(sys.stdin) if u['acronym']=='FASI'))")"
SIAPE="$(printf '%07d' $((RANDOM * 30 % 10000000)))"
code="$(curl -sS -o /dev/null -w '%{http_code}' -b "$JAR" -H 'Content-Type: application/json' \
  -H "X-CSRF-Token: $CSRF" -X POST "$BASE/api/professors" -d "{
    \"full_name\": \"Docente Smoke\", \"siape\": \"$SIAPE\", \"titration\": \"DOUTORADO\",
    \"position\": \"Professor do Magistério Superior\", \"unit_id\": \"$unit_id\",
    \"faculty\": \"FASI\", \"campus\": \"Cametá\", \"work_regime\": \"DE\"}")"
[ "$code" = "201" ] || fail "creating professor returned $code"
compose exec -T backend sh -c 'echo smoke > /app/storage/smoke.txt' || fail "cannot write to storage volume"
echo "    professor $SIAPE created; file written to storage volume"

echo "==> upload body limit (DOC-03: 120 MB at nginx)"
head -c $((25 * 1024 * 1024)) /dev/zero > "$WORK/body25.bin"
head -c $((121 * 1024 * 1024)) /dev/zero > "$WORK/body121.bin"
no_process="00000000-0000-0000-0000-000000000000"
upload_code() {
  curl -sS -o /dev/null -w '%{http_code}' -b "$JAR" -H "X-CSRF-Token: $CSRF" \
    -F "file=@$1;type=application/pdf" "$BASE/api/processes/$no_process/documents"
}
# 25 MB passes nginx and reaches the backend, which answers 404 for the unknown process.
code="$(upload_code "$WORK/body25.bin")"
[ "$code" = "404" ] || fail "25 MB upload returned $code (expected 404 from the backend, not nginx 413)"
# Above 120 MB nginx refuses the request before it reaches the backend.
code="$(upload_code "$WORK/body121.bin")"
[ "$code" = "413" ] || fail "121 MB upload returned $code (expected 413 from nginx)"
echo "    25 MB reaches the backend (404); 121 MB gets 413 from nginx"

echo "==> down (without -v) and up again"
compose down
up_start=$SECONDS
compose up -d
wait_health "$up_start"
login
curl -fsS -b "$JAR" "$BASE/api/professors" | python3 -c "
import json, sys
sys.exit(0 if any(p['siape'] == '$SIAPE' for p in json.load(sys.stdin)) else 1)" \
  || fail "professor $SIAPE not found after restart"
[ "$(compose exec -T backend cat /app/storage/smoke.txt)" = "smoke" ] || fail "storage file lost after restart"
echo "    professor and storage file preserved"

echo "PASS: smoke"
