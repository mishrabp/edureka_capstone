#!/bin/bash
set -e

# 1. Start FastAPI backend in the background
echo "Starting Backend (FastAPI) on port 8001..."
uvicorn app.main:app --host 0.0.0.0 --port 8001 &

# 2. Dynamic Health Check: Wait for backend to be ready
echo "Waiting for backend to warm up (loading embedding models)..."
MAX_RETRIES=60
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if curl -s http://localhost:8001/api/v1/health > /dev/null; then
    echo "Backend is healthy! ✓"
    break
  fi
  RETRY_COUNT=$((RETRY_COUNT+1))
  sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "Backend failed to start in time. Exiting."
  exit 1
fi

# 3. Start Streamlit frontend
echo "Starting Frontend (Streamlit) on port 7860..."
streamlit run frontend/app.py --server.port 7860 --server.address 0.0.0.0
