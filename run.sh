#!/usr/bin/env bash
# run.sh — Start the Agentic RAG backend and frontend together
# Usage: bash run.sh   (do NOT source with ". ./run.sh")

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BACKEND_PORT=8001
FRONTEND_PORT=8501
LOG_DIR="$SCRIPT_DIR/logs"

mkdir -p "$LOG_DIR"

# ── Detect Python / conda ─────────────────────────────────────────────────────
if conda info --envs >/dev/null 2>&1; then
    USE_CONDA=true
else
    USE_CONDA=false
fi

_run() {
    if $USE_CONDA; then
        conda run -n base "$@"
    else
        "$@"
    fi
}

# ── Check .env ────────────────────────────────────────────────────────────────
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "   → Please edit .env and set your GOOGLE_API_KEY, then re-run."
    return 2 2>/dev/null || exit 2
fi

# ── Kill any process currently on our ports ───────────────────────────────────
kill_port() {
    local port=$1
    echo "🔍 Releasing port $port..."
    # Attempt 1: lsof (cleaner, user-owned only usually)
    local pids=$(lsof -t -i:$port 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "   → Killing PIDs on $port: $pids"
        echo "$pids" | xargs -r kill -9 2>/dev/null || true
        sleep 1
    fi
    # Attempt 2: fuser (often more aggressive/found hidden ones)
    fuser -k "$port/tcp" >/dev/null 2>&1 || true
    sleep 0.5
}

# ── Ensure port is free ───────────────────────────────────────────────────────
wait_for_port_free() {
    local port=$1
    local timeout=5
    local count=0
    while lsof -i :$port >/dev/null 2>&1; do
        if [ "$count" -ge "$timeout" ]; then
            echo "❌ Port $port is STICKY and could not be cleared."
            return 1
        fi
        echo "   ... waiting for $port to release"
        kill_port "$port"
        sleep 1
        ((count++))
    done
    return 0
}

kill_port "$BACKEND_PORT"
kill_port "$FRONTEND_PORT"
wait_for_port_free "$BACKEND_PORT" || exit 1
wait_for_port_free "$FRONTEND_PORT" || exit 1


# ── Cleanup on Ctrl+C / exit ──────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "Shutting down..."
    [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
    echo "All processes stopped. Logs → $LOG_DIR/"
}
trap cleanup EXIT INT TERM

# ── Start backend ─────────────────────────────────────────────────────────────
echo "🚀 Starting FastAPI backend on http://localhost:$BACKEND_PORT ..."
_run uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --reload \
    > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

# Wait until health check succeeds (max 60 s)
echo -n "   Waiting for backend to be ready"
READY=false
for i in $(seq 1 30); do
    sleep 2
    if curl -sf "http://localhost:$BACKEND_PORT/api/v1/health" >/dev/null 2>&1; then
        echo " ✓"
        READY=true
        break
    fi
    echo -n "."
done

if [ "$READY" = false ]; then
    echo ""
    echo "❌ Backend failed to start after 60s. Last log:"
    tail -30 "$LOG_DIR/backend.log"
    return 1 2>/dev/null || exit 1
fi

# ── Start frontend ────────────────────────────────────────────────────────────
echo "🖥️  Starting Streamlit frontend on http://localhost:$FRONTEND_PORT ..."
_run streamlit run frontend/app.py \
    --server.port "$FRONTEND_PORT" \
    --server.address 0.0.0.0 \
    --server.headless true \
    > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

# ── Ready ─────────────────────────────────────────────────────────────────────
echo ""
echo "=========================================="
echo "  ✅  Clinical RAG App is running!"
echo "=========================================="
echo "  Backend  (FastAPI)  : http://localhost:$BACKEND_PORT"
echo "  API Docs (Swagger)  : http://localhost:$BACKEND_PORT/docs"
echo "  Frontend (Streamlit): http://localhost:$FRONTEND_PORT"
echo "  Logs                : $LOG_DIR/"
echo ""
echo "  Press Ctrl+C to stop."
echo "=========================================="

wait "$BACKEND_PID" "$FRONTEND_PID"
