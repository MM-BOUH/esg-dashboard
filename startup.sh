#!/usr/bin/env bash
# Start uvicorn first so Render detects the port, then run setup in background.
# seed_mongo and build_index are idempotent so re-running is safe.

echo "==> Starting FastAPI..."
uvicorn assistant.api.main:app --host 0.0.0.0 --port "${PORT:-8000}" &
SERVER_PID=$!

echo "==> Seeding MongoDB..."
python -m assistant.scripts.seed_mongo

echo "==> Building ChromaDB index..."
python -m assistant.scripts.build_index

echo "==> Setup complete."
wait $SERVER_PID
