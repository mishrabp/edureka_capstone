#!/bin/bash
set -e

# 1. Start FastAPI backend in the background
# We bind to 0.0.0.0:8001 as the frontend expects this by default
echo "Starting Backend (FastAPI)..."
uvicorn app.main:app --host 0.0.0.0 --port 8001 &

# 2. Wait for backend to be ready
echo "Waiting for backend to warm up..."
sleep 5

# 3. Start Streamlit frontend
# HF Spaces expect the main app on port 7860
echo "Starting Frontend (Streamlit)..."
streamlit run frontend/app.py --server.port 7860 --server.address 0.0.0.0
