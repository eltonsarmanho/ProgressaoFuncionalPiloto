FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Runtime dependencies only: test and lint tools stay out of the image.
COPY requirements.txt .
RUN grep -vE '^(pytest|ruff)==' requirements.txt > /tmp/requirements.runtime.txt \
    && pip install -r /tmp/requirements.runtime.txt \
    && rm /tmp/requirements.runtime.txt

RUN useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /app/storage \
    && chown app:app /app/storage

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

USER app
EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
