#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "============================================"
echo "  AidSec Lead Dashboard - Starting..."
echo "============================================"
echo ""

# Load .env if present
if [ -f ".env" ]; then
    echo "[*] Loading .env config..."
    set -a
    source .env
    set +a
fi

cleanup() {
    echo ""
    echo "Stopping services..."
    kill "$API_PID" 2>/dev/null || true
    kill "$UI_PID" 2>/dev/null || true
    echo "Services stopped."
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "[1/2] Starting FastAPI Backend on port 8000..."
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

sleep 2

echo "[2/2] Starting Streamlit Frontend on port 8501..."
python -m streamlit run app.py \
    --server.address 0.0.0.0 \
    --server.port 8501 \
    --browser.gatherUsageStats false &
UI_PID=$!

LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "YOUR_IP")

echo ""
echo "============================================"
echo "  Dashboard running!"
echo "  UI:  http://localhost:8501"
echo "  API: http://localhost:8000/api/docs"
echo ""
echo "  Team access (same network):"
echo "  UI:  http://${LOCAL_IP}:8501"
echo "  API: http://${LOCAL_IP}:8000/api/docs"
echo "============================================"
echo ""
echo "Press Ctrl+C to stop..."

wait
