#!/usr/bin/env bash
# Render start script for the FastAPI backend.
# Runs data setup on every cold start, then launches the server.
# Both seed_mongo and build_index are idempotent so re-running is safe.

set -e

echo "==> Seeding MongoDB..."
python -m assistant.scripts.seed_mongo

echo "==> Building ChromaDB index..."
python -m assistant.scripts.build_index

echo "==> Starting FastAPI..."
exec uvicorn assistant.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
