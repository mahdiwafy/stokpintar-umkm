#!/usr/bin/env bash
set -e

PORT=${PORT:-8090}
HOST=${HOST:-0.0.0.0}

echo "=== Starting StokPintar UMKM Server ==="
echo "Port: $PORT"
echo "Host: $HOST"
echo "Documentation: http://localhost:$PORT/docs"

exec python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
