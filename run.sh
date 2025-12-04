#!/bin/bash

# Simple helper script to run the AI Roadmap Service locally

# Kill any existing process on port 8003 (ignore errors if none)
lsof -ti :8003 | xargs kill -9 2>/dev/null || true
sleep 1

# Activate virtual environment if present
if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

# Start the backend server
PYTHONPATH="$(pwd):$PYTHONPATH" uvicorn src.main:app --reload --port 8003 --host 0.0.0.0


