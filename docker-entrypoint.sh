#!/bin/sh
# Apply database migrations (and optionally demo data) before starting the server.
set -e

alembic upgrade head

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  python -m app.seed
fi

exec "$@"
