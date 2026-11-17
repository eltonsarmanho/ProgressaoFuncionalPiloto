#!/usr/bin/env bash
# Smoke test for the backend image (INFRA-02): build, run against a throwaway
# postgres, expect healthy /api/health with migrations at head. Cleans up on exit.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SUFFIX="$$"
IMAGE="progressao-backend:smoke-${SUFFIX}"
NET="pd_smoke_backend_net_${SUFFIX}"
DB="pd_smoke_backend_db_${SUFFIX}"
API="pd_smoke_backend_api_${SUFFIX}"

cleanup() {
  docker rm -f "$API" "$DB" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
  docker rmi "$IMAGE" >/dev/null 2>&1 || true
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  docker logs "$API" 2>&1 | tail -40 >&2 || true
  exit 1
}

echo "==> build $IMAGE"
docker build -q -t "$IMAGE" "$ROOT/backend" >/dev/null

docker network create "$NET" >/dev/null
docker run -d --name "$DB" --network "$NET" \
  -e POSTGRES_USER=smoke -e POSTGRES_PASSWORD=smoke -e POSTGRES_DB=smoke \
  postgres:16-alpine >/dev/null

# Backend starts before postgres is ready on purpose: the entrypoint must wait.
docker run -d --name "$API" --network "$NET" -p 127.0.0.1::8000 \
  -e DATABASE_URL="postgresql+psycopg://smoke:smoke@${DB}:5432/smoke" \
  -e ADMIN_EMAIL=admin@smoke.local -e ADMIN_PASSWORD=smoke-password-123 \
  -e COOKIE_SECURE=false \
  "$IMAGE" >/dev/null

PORT="$(docker port "$API" 8000/tcp | head -1 | sed 's/.*://')"
echo "==> waiting for http://127.0.0.1:${PORT}/api/health"
body=""
for _ in $(seq 1 120); do
  [ "$(docker inspect -f '{{.State.Running}}' "$API")" = "true" ] || fail "backend container exited"
  if body="$(curl -fsS "http://127.0.0.1:${PORT}/api/health" 2>/dev/null)"; then break; fi
  body=""
  sleep 1
done
[ -n "$body" ] || fail "health did not return 200 within 120 s"
expected='{"status":"ok","database":"ok"}'
[ "$body" = "$expected" ] || fail "unexpected health body: $body"
echo "    health 200 $body"

head_rev="$(docker exec "$API" alembic heads | awk '{print $1}')"
db_rev="$(docker exec "$DB" psql -U smoke -d smoke -tAc 'SELECT version_num FROM alembic_version')"
[ -n "$head_rev" ] && [ "$db_rev" = "$head_rev" ] || fail "migrations not at head (db=$db_rev head=$head_rev)"
echo "    alembic at head ($db_rev)"

uid="$(docker exec "$API" id -u)"
[ "$uid" != "0" ] || fail "backend runs as root"
echo "    runs as uid $uid"

echo "PASS: smoke_backend"
