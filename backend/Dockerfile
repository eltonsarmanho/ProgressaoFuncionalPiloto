FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# OCR (PIPE-06): Tesseract with the Portuguese model only. `--no-install-recommends`
# skips optional packages; the English and orientation models pulled in as
# dependencies are dropped in the same layer (the OCR adapter uses `-l por`), and
# the apt lists are removed, to keep the image small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-por \
    && find /usr/share/tesseract-ocr -type f \( -name 'eng.traineddata' -o -name 'osd.traineddata' \) -delete \
    && rm -rf /var/lib/apt/lists/*

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
