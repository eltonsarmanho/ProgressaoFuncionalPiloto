#!/bin/sh
# Wait for the database, apply migrations, seed reference data, then serve (INFRA-02).
set -eu

python - <<'PY'
import os
import sys
import time

import psycopg

url = os.environ.get("DATABASE_URL")
if not url:
    sys.exit("Configuração inválida: variáveis de ambiente ausentes ou inválidas: DATABASE_URL")
dsn = url.replace("postgresql+psycopg://", "postgresql://", 1)
deadline = time.monotonic() + int(os.environ.get("DB_WAIT_SECONDS", "60"))
while True:
    try:
        psycopg.connect(dsn, connect_timeout=3).close()
        break
    except psycopg.OperationalError:
        if time.monotonic() > deadline:
            sys.exit("Banco de dados indisponível")
        print("Aguardando o banco de dados...", flush=True)
        time.sleep(1)
PY

alembic upgrade head
python -m app.infrastructure.database.seed
exec uvicorn --factory app.main:create_app --host 0.0.0.0 --port 8000
