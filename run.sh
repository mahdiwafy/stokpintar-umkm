#!/usr/bin/env bash
set -e

# Change directory to script location
cd "$(dirname "$0")"

PORT=${PORT:-8090}
HOST=${HOST:-0.0.0.0}

echo "=== StokPintar UMKM — Auto Setup & Launch ==="

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 tidak ditemukan. Silakan install Python 3.10+ terlebih dahulu."
    exit 1
fi

# Setup Virtual Environment automatically if not inside one
if [ -z "$VIRTUAL_ENV" ]; then
    if [ ! -d ".venv" ]; then
        echo "[1/3] Membuat virtual environment (.venv)..."
        python3 -m venv .venv
    fi
    echo "[2/3] Mengaktifkan virtual environment..."
    source .venv/bin/activate
fi

# Auto-install dependencies if fastapi or uvicorn not found
if ! python3 -c "import fastapi, uvicorn, pydantic, httpx" &> /dev/null; then
    echo "[3/3] Menginstall dependensi dari requirements.txt..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "[3/3] Seluruh dependensi sudah siap."
fi

echo ""
echo "======================================================"
echo " Aplikasi Web : http://localhost:$PORT"
echo " Swagger API  : http://localhost:$PORT/docs"
echo " Database     : data/stok_umkm.db (Auto-created & Seeded)"
echo "======================================================"
echo ""

exec python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
