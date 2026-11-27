#!/bin/sh
set -eu

python -c 'from app.core.config import settings; print("Configuration validated: " + settings.APP_ENV)'
alembic upgrade head
exec "$@"
