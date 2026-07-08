#!/bin/bash
set -e

GUNICORN_CMD_ARGS=${GUNICORN_CMD_ARGS:-""} # ex: --log-config app/log.conf

# Allow running locally without env vars.
PROMETHEUS_MULTIPROC_DIR=${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus_multiproc}
mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
# Empty prometheus dir if it exists, to prevent ghost metrics being ingested twice in case of docker restart
rm -rf "${PROMETHEUS_MULTIPROC_DIR:?}"/*

if [[ -f "scripts/gunicorn.conf.py" ]]; then
  GUNICORN_CONFIG="scripts/gunicorn.conf.py"
elif [[ -f "/scripts/gunicorn.conf.py" ]]; then
  GUNICORN_CONFIG="/scripts/gunicorn.conf.py"
else
  echo "Error: gunicorn config not found (expected scripts/gunicorn.conf.py or /scripts/gunicorn.conf.py)" >&2
  exit 1
fi

exec gunicorn opengaterag.api.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --config "$GUNICORN_CONFIG" $GUNICORN_CMD_ARGS
